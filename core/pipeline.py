"""Pipeline modular de transformações de imagem para gravação a laser.

Cada transformação é um módulo independente com estado `enabled` (ON/OFF) e
parâmetros próprios, permitindo experimentar livremente combinações entre
fotorealismo e durabilidade minimalista e salvar receitas em presets.
"""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Dict, List
import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Funções puras de transformação
# ---------------------------------------------------------------------------

def transform_brightness_contrast(
    bgr_img: np.ndarray,
    brightness: int = 50,
    contrast: int = 50,
) -> np.ndarray:
    """Ajusta brilho (0..100, neutro 50) e contraste (0..100, neutro 50)."""
    if brightness == 50 and contrast == 50:
        return bgr_img
    adj_b = brightness - 50
    adj_c = contrast - 50
    beta = adj_b * 2.55
    alpha = 1.0 + adj_c / 50.0
    return cv2.convertScaleAbs(bgr_img, alpha=alpha, beta=beta)


def transform_channel_mixing(
    bgr_img: np.ndarray,
    r_weight: float = 0.6,
    g_weight: float = 0.3,
    b_weight: float = 0.1,
) -> np.ndarray:
    """Converte BGR para escala de cinza com pesos customizados (padrão pele: 60/30/10)."""
    b, g, r = cv2.split(bgr_img)
    mixed = r.astype(np.float32) * float(r_weight) + g.astype(np.float32) * float(g_weight) + b.astype(np.float32) * float(b_weight)
    return np.clip(mixed, 0.0, 255.0).astype(np.uint8)


def transform_clahe(
    gray_img: np.ndarray,
    clip_limit: float = 2.0,
    tile_size: int = 8,
) -> np.ndarray:
    """Equalização adaptativa de contraste local (CLAHE)."""
    ts = max(2, int(tile_size))
    cl = max(0.1, float(clip_limit))
    clahe = cv2.createCLAHE(clipLimit=cl, tileGridSize=(ts, ts))
    return clahe.apply(gray_img)


def transform_gamma(
    gray_img: np.ndarray,
    gamma: float = 1.2,
) -> np.ndarray:
    """Correção gama configurável (gamma=1.0 é neutro)."""
    g = max(0.1, float(gamma))
    if abs(g - 1.0) < 1e-4:
        return gray_img
    inv_gamma = 1.0 / g
    table = np.array([((i / 255.0) ** inv_gamma) * 255.0 for i in range(256)], dtype=np.uint8)
    return cv2.LUT(gray_img, table)


def transform_density(
    gray_img: np.ndarray,
    level: int = 1,
) -> np.ndarray:
    """Escurecimento linear de densidade para gravação mais carregada (1..10)."""
    lvl = int(level)
    if lvl <= 1:
        return gray_img
    offset = (lvl - 1) * 10
    return cv2.subtract(gray_img, offset)


def transform_sharpen(
    gray_img: np.ndarray,
    amount: int = 85,
    high_pass: bool = True,
    hp_sigma: float = 1.5,
    usm_sigma: float = 1.0,
) -> np.ndarray:
    """Nitidez configurável: High Pass + Unsharp Mask com bypass real em zero."""
    amt = max(0, int(amount))
    if amt <= 0 and not high_pass:
        return gray_img

    gray_f = gray_img.astype(np.float32)
    if high_pass:
        blurred = cv2.GaussianBlur(gray_f, (0, 0), hp_sigma)
        base = np.clip(gray_f + (gray_f - blurred), 0.0, 255.0)
    else:
        base = gray_f

    if amt > 0:
        usm_amount = (amt / 100.0) * 3.0
        blurred_usm = cv2.GaussianBlur(base, (0, 0), usm_sigma)
        sharpened = base + usm_amount * (base - blurred_usm)
    else:
        sharpened = base

    return np.clip(np.rint(sharpened), 0.0, 255.0).astype(np.uint8)


def transform_bilateral(
    gray_img: np.ndarray,
    passes: int = 3,
    sigma: int = 45,
) -> np.ndarray:
    """Suavização preservadora de bordas (reduz poros/texturas mantendo contornos)."""
    n_passes = max(0, int(passes))
    if n_passes <= 0:
        return gray_img
    sig = max(5.0, float(sigma))
    out = gray_img
    for _ in range(n_passes):
        out = cv2.bilateralFilter(out, d=5, sigmaColor=sig, sigmaSpace=sig)
    return out


def transform_tone_clamp(
    gray_img: np.ndarray,
    black_clamp: int = 20,
    white_clamp: int = 240,
) -> np.ndarray:
    """Trava extremos para preto puro (0) e branco puro (255) via LUT."""
    bc = max(0, min(254, int(black_clamp)))
    wc = max(1, min(255, int(white_clamp)))
    if bc == 0 and wc == 255:
        return gray_img
    if bc >= wc:
        bc = max(0, wc - 1)

    lut = np.arange(256, dtype=np.uint8)
    lut[: bc + 1] = 0
    lut[wc:] = 255
    return cv2.LUT(gray_img, lut)


def _compute_kmeans_1d_centroids(
    gray_img: np.ndarray,
    k_mid: int,
    safe_margin: int = 40,
    max_iter: int = 20,
) -> np.ndarray:
    """K-Means 1D determinístico sobre o histograma de 256 bins (< 1 ms)."""
    hist = np.bincount(gray_img.ravel(), minlength=256).astype(np.float64)
    mid_hist = hist[1:255]
    mid_vals = np.arange(1, 255, dtype=np.float64)
    total = float(mid_hist.sum())

    low = float(max(1, min(120, safe_margin)))
    high = float(min(254, max(135, 255 - safe_margin)))

    if total <= 0.0:
        return np.linspace(low, high, k_mid, dtype=np.float64)

    # Inicialização determinística por quantis cumulativos do histograma
    cdf = np.cumsum(mid_hist) / total
    quantiles = np.linspace(1.0 / (k_mid + 1), k_mid / (k_mid + 1), k_mid)
    centroids = np.array(
        [mid_vals[min(len(mid_vals) - 1, int(np.searchsorted(cdf, q)))] for q in quantiles],
        dtype=np.float64,
    )

    # Caso todos os quantis colapsem no mesmo valor (imagem quase uniforme), espalha levemente
    if np.allclose(centroids, centroids[0]):
        centroids = np.linspace(low, high, k_mid, dtype=np.float64)

    for _ in range(max_iter):
        dists = np.abs(mid_vals[:, None] - centroids[None, :])
        labels = np.argmin(dists, axis=1)
        new_centroids = centroids.copy()
        for idx in range(k_mid):
            mask = labels == idx
            w_sum = float(mid_hist[mask].sum())
            if w_sum > 0.0:
                new_centroids[idx] = float(np.dot(mid_vals[mask], mid_hist[mask]) / w_sum)
        if np.max(np.abs(new_centroids - centroids)) < 1e-4:
            centroids = new_centroids
            break
        centroids = new_centroids

    centroids = np.sort(np.clip(centroids, low, high))
    return centroids


def _otsu_threshold_1d(gray_img: np.ndarray) -> float:
    """Limiar de Otsu sobre pixels internos (1..254) com fallback em 127.5."""
    hist = np.bincount(gray_img.ravel(), minlength=256).astype(np.float64)
    mid_hist = hist[1:255]
    total = float(mid_hist.sum())
    if total <= 0.0:
        return 127.5
    vals = np.arange(1, 255, dtype=np.float64)
    w_bg = np.cumsum(mid_hist)
    w_fg = total - w_bg
    sum_total = float(np.dot(vals, mid_hist))
    sum_bg = np.cumsum(vals * mid_hist)

    valid = (w_bg > 0) & (w_fg > 0)
    if not np.any(valid):
        return 127.5
    mean_bg = np.zeros_like(w_bg)
    mean_fg = np.zeros_like(w_fg)
    mean_bg[valid] = sum_bg[valid] / w_bg[valid]
    mean_fg[valid] = (sum_total - sum_bg[valid]) / w_fg[valid]
    between = np.zeros_like(w_bg)
    between[valid] = w_bg[valid] * w_fg[valid] * (mean_bg[valid] - mean_fg[valid]) ** 2
    best_idx = int(np.argmax(between))
    return float(vals[best_idx])


def transform_quantize(
    gray_img: np.ndarray,
    levels: int = 4,
    softness: int = 35,
    mode: str = "kmeans",
    safe_margin: int = 40,
) -> np.ndarray:
    """Quantização tonal determinística com camada opcional de suavização entre níveis.

    - `levels`: número de níveis (2..8; 0 ou <2 desativa).
    - `softness`: 0 = degraus secos (exatamente `<= levels` valores únicos);
      1..100 = rampa cúbica smoothstep nas fronteiras entre níveis, mantendo
      platôs limpos no centro de cada faixa para transição orgânica no Atkinson.
    - `mode`: `"kmeans"` (centroides adaptativos no histograma) ou `"uniform"`.
    """
    n_levels = int(levels)
    if n_levels < 2:
        return gray_img

    soft = max(0.0, min(100.0, float(softness))) / 100.0

    if n_levels == 2:
        all_centroids = np.array([0.0, 255.0], dtype=np.float64)
        thresh = _otsu_threshold_1d(gray_img) if mode == "kmeans" else 127.5
        boundaries = np.array([thresh], dtype=np.float64)
    else:
        k_mid = n_levels - 2
        if mode == "uniform":
            interior = np.linspace(0.0, 255.0, n_levels, dtype=np.float64)[1:-1]
            low = float(max(1, min(120, safe_margin)))
            high = float(min(254, max(135, 255 - safe_margin)))
            interior = np.clip(interior, low, high)
        else:
            interior = _compute_kmeans_1d_centroids(gray_img, k_mid=k_mid, safe_margin=safe_margin)
        all_centroids = np.concatenate(([0.0], interior, [255.0]))
        boundaries = 0.5 * (all_centroids[:-1] + all_centroids[1:])

    x = np.arange(256, dtype=np.float64)
    indices = np.searchsorted(boundaries, x, side="right")
    y = all_centroids[indices].copy()

    if soft > 0.0:
        n_bounds = len(boundaries)
        for k in range(n_bounds):
            m_k = boundaries[k]
            left_limit = boundaries[k - 1] if k > 0 else 0.0
            right_limit = boundaries[k + 1] if k + 1 < n_bounds else 255.0
            half_w = 0.5 * soft * min(m_k - left_limit, right_limit - m_k)
            if half_w <= 1e-6:
                continue
            lo = m_k - half_w
            hi = m_k + half_w
            mask = (x >= lo) & (x <= hi)
            if np.any(mask):
                t = (x[mask] - lo) / (2.0 * half_w)
                smooth = t * t * (3.0 - 2.0 * t)
                y[mask] = all_centroids[k] + smooth * (all_centroids[k + 1] - all_centroids[k])

    # Garante extremos puros intactos (fundo branco e preto sólido)
    y[0] = 0.0
    y[255] = 255.0

    lut = np.clip(np.rint(y), 0.0, 255.0).astype(np.uint8)
    return cv2.LUT(gray_img, lut)


def transform_cleanup(
    gray_img: np.ndarray,
    method: str = "morph_close_open",
    kernel_size: int = 3,
) -> np.ndarray:
    """Limpeza de micro-ilhas/ruído via Morfologia (Close+Open) ou Filtro Mediano."""
    k = 5 if int(kernel_size) >= 5 else 3
    if method == "median":
        return cv2.medianBlur(gray_img, k)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    closed = cv2.morphologyEx(gray_img, cv2.MORPH_CLOSE, kernel)
    return cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)


# ---------------------------------------------------------------------------
# Registro Modular de Transformações
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TransformSpec:
    id: str
    label: str
    stage: str  # "color" ou "gray"
    default_enabled: bool
    default_params: Dict[str, Any]
    fn: Callable[..., np.ndarray]


TRANSFORM_SPECS: List[TransformSpec] = [
    TransformSpec(
        id="brightness_contrast",
        label="Brilho & Contraste",
        stage="color",
        default_enabled=False,
        default_params={"brightness": 50, "contrast": 50},
        fn=transform_brightness_contrast,
    ),
    TransformSpec(
        id="channel_mixing",
        label="Mixagem de Canais (Pele)",
        stage="color",
        default_enabled=False,
        default_params={"r_weight": 0.6, "g_weight": 0.3, "b_weight": 0.1},
        fn=transform_channel_mixing,
    ),
    TransformSpec(
        id="clahe",
        label="CLAHE (Contraste Local)",
        stage="gray",
        default_enabled=False,
        default_params={"clip_limit": 2.0, "tile_size": 8},
        fn=transform_clahe,
    ),
    TransformSpec(
        id="gamma",
        label="Correção Gama",
        stage="gray",
        default_enabled=False,
        default_params={"gamma": 1.2},
        fn=transform_gamma,
    ),
    TransformSpec(
        id="density",
        label="Densidade",
        stage="gray",
        default_enabled=False,
        default_params={"level": 1},
        fn=transform_density,
    ),
    TransformSpec(
        id="sharpen",
        label="Nitidez (Unsharp / HP)",
        stage="gray",
        default_enabled=False,
        default_params={"amount": 85, "high_pass": True},
        fn=transform_sharpen,
    ),
    TransformSpec(
        id="bilateral",
        label="Suavização Bilateral",
        stage="gray",
        default_enabled=False,
        default_params={"passes": 3, "sigma": 45},
        fn=transform_bilateral,
    ),
    TransformSpec(
        id="tone_clamp",
        label="Trava de Extremos",
        stage="gray",
        default_enabled=False,
        default_params={"black_clamp": 20, "white_clamp": 240},
        fn=transform_tone_clamp,
    ),
    TransformSpec(
        id="quantize",
        label="Quantização Suave",
        stage="gray",
        default_enabled=False,
        default_params={"levels": 4, "softness": 35, "mode": "kmeans"},
        fn=transform_quantize,
    ),
    TransformSpec(
        id="cleanup",
        label="Limpeza (Ilhas / Ruído)",
        stage="gray",
        default_enabled=False,
        default_params={"method": "morph_close_open", "kernel_size": 3},
        fn=transform_cleanup,
    ),
]

TRANSFORM_REGISTRY: Dict[str, TransformSpec] = {spec.id: spec for spec in TRANSFORM_SPECS}


def default_transforms_config(overrides: Dict[str, Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Retorna a lista padrão de configuração dos módulos, aplicando overrides opcionais.

    Exemplo de `overrides`:
        {"clahe": {"enabled": False}, "tone_clamp": {"enabled": True, "params": {"white_clamp": 242}}}
    """
    overrides = overrides or {}
    result: List[Dict[str, Any]] = []
    for spec in TRANSFORM_SPECS:
        ov = overrides.get(spec.id, {})
        params = deepcopy(spec.default_params)
        if "params" in ov and isinstance(ov["params"], dict):
            params.update(ov["params"])
        enabled = bool(ov.get("enabled", spec.default_enabled))
        result.append({"id": spec.id, "enabled": enabled, "params": params})
    return result


def get_transform_entry(transforms_cfg: List[Dict[str, Any]], transform_id: str) -> Dict[str, Any]:
    """Localiza um módulo pelo ID dentro da lista de configurações."""
    for entry in transforms_cfg:
        if entry.get("id") == transform_id:
            return entry
    raise KeyError(f"Transformação desconhecida: {transform_id}")


def normalize_transforms_config(settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normaliza `settings` (formato modular `transforms` ou formato plano CLI/testes)
    em uma lista completa e ordenada de configurações de módulos válida.
    """
    raw_list = settings.get("transforms")
    if isinstance(raw_list, list) and len(raw_list) > 0:
        normalized: List[Dict[str, Any]] = []
        seen = set()
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            tid = item.get("id")
            if tid not in TRANSFORM_REGISTRY or tid in seen:
                continue
            spec = TRANSFORM_REGISTRY[tid]
            params = deepcopy(spec.default_params)
            if isinstance(item.get("params"), dict):
                params.update(item["params"])
            normalized.append({
                "id": tid,
                "enabled": bool(item.get("enabled", spec.default_enabled)),
                "params": params,
            })
            seen.add(tid)

        # Completa eventuais módulos novos que não estavam presentes
        for spec in TRANSFORM_SPECS:
            if spec.id not in seen:
                normalized.append({
                    "id": spec.id,
                    "enabled": spec.default_enabled,
                    "params": deepcopy(spec.default_params),
                })
        return normalized

    # Fallback para dicionário plano (usado pela CLI ou chamadas programáticas simples)
    cfg = default_transforms_config()
    by_id = {entry["id"]: entry for entry in cfg}

    if "brightness" in settings or "contrast" in settings:
        by_id["brightness_contrast"]["enabled"] = True
        if "brightness" in settings:
            by_id["brightness_contrast"]["params"]["brightness"] = int(settings["brightness"])
        if "contrast" in settings:
            by_id["brightness_contrast"]["params"]["contrast"] = int(settings["contrast"])

    if "channel_mixing_enabled" in settings:
        by_id["channel_mixing"]["enabled"] = bool(settings["channel_mixing_enabled"])

    if "clahe_enabled" in settings:
        by_id["clahe"]["enabled"] = bool(settings["clahe_enabled"])
    if "clahe_clip_limit" in settings:
        by_id["clahe"]["params"]["clip_limit"] = float(settings["clahe_clip_limit"])
    if "clahe_tile_size" in settings:
        by_id["clahe"]["params"]["tile_size"] = int(settings["clahe_tile_size"])

    if "gamma_active" in settings:
        by_id["gamma"]["enabled"] = bool(settings["gamma_active"])
    if "gamma_value" in settings:
        by_id["gamma"]["params"]["gamma"] = float(settings["gamma_value"])

    if "density" in settings:
        d = int(settings["density"])
        by_id["density"]["enabled"] = d > 1
        by_id["density"]["params"]["level"] = d

    if "sharpen" in settings:
        sh = int(settings["sharpen"])
        by_id["sharpen"]["enabled"] = sh > 0
        by_id["sharpen"]["params"]["amount"] = sh
    if "sharpen_high_pass" in settings:
        by_id["sharpen"]["params"]["high_pass"] = bool(settings["sharpen_high_pass"])

    if "bilateral_passes" in settings:
        bp = int(settings["bilateral_passes"])
        by_id["bilateral"]["enabled"] = bp > 0
        if bp > 0:
            by_id["bilateral"]["params"]["passes"] = bp
    if "bilateral_sigma" in settings:
        by_id["bilateral"]["params"]["sigma"] = int(settings["bilateral_sigma"])

    if "white_clamp" in settings or "black_clamp" in settings:
        wc = int(settings.get("white_clamp", 255))
        bc = int(settings.get("black_clamp", 0))
        by_id["tone_clamp"]["enabled"] = (bc > 0 or wc < 255)
        by_id["tone_clamp"]["params"]["black_clamp"] = bc
        by_id["tone_clamp"]["params"]["white_clamp"] = wc

    if "quantize_levels" in settings:
        ql = int(settings["quantize_levels"])
        by_id["quantize"]["enabled"] = ql >= 2
        if ql >= 2:
            by_id["quantize"]["params"]["levels"] = ql
    if "quantize_softness" in settings:
        by_id["quantize"]["params"]["softness"] = int(settings["quantize_softness"])
    if "quantize_mode" in settings:
        by_id["quantize"]["params"]["mode"] = str(settings["quantize_mode"])

    if "cleanup_method" in settings:
        cm = str(settings["cleanup_method"])
        if cm in ("morph_close_open", "median"):
            by_id["cleanup"]["enabled"] = True
            by_id["cleanup"]["params"]["method"] = cm
        elif cm == "off":
            by_id["cleanup"]["enabled"] = False
    elif "morph_clean" in settings:
        by_id["cleanup"]["enabled"] = bool(settings["morph_clean"])
    if "cleanup_kernel" in settings:
        by_id["cleanup"]["params"]["kernel_size"] = int(settings["cleanup_kernel"])

    return cfg


def run_transform_pipeline(
    cv2_bgr: np.ndarray,
    transforms_cfg: List[Dict[str, Any]],
) -> np.ndarray:
    """Executa o estágio de cor -> cinza seguido dos módulos em cinza na ordem configurada."""
    by_id = {entry["id"]: entry for entry in transforms_cfg if entry.get("id") in TRANSFORM_REGISTRY}

    # 1. Brilho & Contraste (BGR)
    img_bgr = cv2_bgr
    bc_cfg = by_id.get("brightness_contrast")
    if bc_cfg and bc_cfg.get("enabled", False):
        p = bc_cfg.get("params", {})
        img_bgr = transform_brightness_contrast(
            img_bgr,
            brightness=p.get("brightness", 50),
            contrast=p.get("contrast", 50),
        )

    # 2. Conversão Cor -> Escala de Cinza (Mixagem de Canais vs BT.601 padrão)
    cm_cfg = by_id.get("channel_mixing")
    if cm_cfg and cm_cfg.get("enabled", False):
        p = cm_cfg.get("params", {})
        gray = transform_channel_mixing(
            img_bgr,
            r_weight=p.get("r_weight", 0.6),
            g_weight=p.get("g_weight", 0.3),
            b_weight=p.get("b_weight", 0.1),
        )
    else:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # 3. Estágio modular em escala de cinza (respeita a ordem exata da lista)
    for entry in transforms_cfg:
        tid = entry.get("id")
        spec = TRANSFORM_REGISTRY.get(tid)
        if spec is None or spec.stage != "gray":
            continue
        if not entry.get("enabled", False):
            continue
        params = entry.get("params", {})
        gray = spec.fn(gray, **params)

    return gray
