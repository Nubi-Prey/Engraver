import io
import math
import cv2
import numpy as np
from PIL import Image, ImageChops, ImageCms, ImageFile, ImageOps
from PIL import (
    BmpImagePlugin,
    GifImagePlugin,
    JpegImagePlugin,
    PngImagePlugin,
    TiffImagePlugin,
    WebPImagePlugin,
)
from core.dither_backend import dither_atkinson, dither_jarvis

# Tolera JPEGs levemente truncados comuns em downloads de mensageiros (ex.: WhatsApp)
ImageFile.LOAD_TRUNCATED_IMAGES = True


def _safe_load_rational(ifd, data, legacy_api=True):
    """Loader EXIF/TIFF RATIONAL (tipo 5) plano, sem closure/generator/IFDRational.

    Evita SIGSEGV observado no binário compilado com Nuitka + PySide6/Shiboken6
    quando o Pillow decodifica tags RATIONAL (ex.: XResolution) dentro de um slot Qt.
    """
    vals = ifd._unpack(f"{len(data) // 4}L", data)
    result = []
    for i in range(0, len(vals) - 1, 2):
        num = vals[i]
        denom = vals[i + 1]
        if legacy_api:
            result.append((num, denom))
        else:
            result.append(float(num) / denom if denom else float("nan"))
    return tuple(result)


def _safe_load_signed_rational(ifd, data, legacy_api=True):
    """Loader EXIF/TIFF SRATIONAL (tipo 10) plano, sem closure/generator/IFDRational."""
    vals = ifd._unpack(f"{len(data) // 4}l", data)
    result = []
    for i in range(0, len(vals) - 1, 2):
        num = vals[i]
        denom = vals[i + 1]
        if legacy_api:
            result.append((num, denom))
        else:
            result.append(float(num) / denom if denom else float("nan"))
    return tuple(result)


def _patch_pillow_rational_loaders():
    dispatch = TiffImagePlugin.ImageFileDirectory_v2._load_dispatch
    dispatch[5] = (8, _safe_load_rational)
    dispatch[10] = (8, _safe_load_signed_rational)


# Pré-inicializa os decodificadores e plugins do Pillow estaticamente
Image.init()
_patch_pillow_rational_loaders()


def _sanitize_dpi(raw_dpi, default=(72.0, 72.0)):
    """Converte metadados de DPI em tupla (float, float) finita e positiva."""
    try:
        if isinstance(raw_dpi, (tuple, list)) and len(raw_dpi) >= 2:
            x, y = float(raw_dpi[0]), float(raw_dpi[1])
        elif raw_dpi is not None:
            x = y = float(raw_dpi)
        else:
            return default
        if not (math.isfinite(x) and math.isfinite(y)) or x <= 0 or y <= 0:
            return default
        return (x, y)
    except (TypeError, ValueError, ZeroDivisionError):
        return default


def normalize_image_input(pil_img):
    """Normaliza imagens profissionais e amadoras preservando fidelidade máxima.

    - Aplica orientação EXIF (ImageOps.exif_transpose)
    - Converte 16-bit (I;16/I) para 8-bit linearmente sem clipar
    - Preserva transparência de imagens em modo paleta (P/PA/LA -> RGBA)
    - Converte perfis ICC (Adobe RGB, Display P3, ProPhoto RGB, CMYK) para sRGB via LCMS2
    """
    icc_bytes = pil_img.info.get("icc_profile")

    # 1. Orientação EXIF (câmeras DSLR e smartphones)
    try:
        pil_img = ImageOps.exif_transpose(pil_img)
    except Exception:
        pass

    # 2. Normalização de profundidade 16-bit -> 8-bit
    if pil_img.mode.startswith("I;16") or pil_img.mode == "I":
        arr = np.array(pil_img, dtype=np.float32)
        max_val = float(arr.max()) if arr.size > 0 else 0.0
        if max_val > 255.0:
            scale = 65535.0 if pil_img.mode.startswith("I;16") or max_val <= 65535.0 else max_val
            arr = np.clip((arr / scale) * 255.0, 0.0, 255.0)
        else:
            arr = np.clip(arr, 0.0, 255.0)
        pil_img = Image.fromarray(arr.astype(np.uint8), mode="L")
        icc_bytes = None

    # 3. Transparência em paletas e escala de cinza com alfa
    if pil_img.mode == "P":
        if "transparency" in pil_img.info:
            pil_img = pil_img.convert("RGBA")
        else:
            pil_img = pil_img.convert("RGB")
    elif pil_img.mode in ("PA", "LA"):
        pil_img = pil_img.convert("RGBA")

    # 4. Conversão de perfil de cor ICC -> sRGB (preservando fidelidade de fotos profissionais)
    if icc_bytes and pil_img.mode in ("RGB", "RGBA", "CMYK"):
        try:
            src_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc_bytes))
            srgb_profile = ImageCms.createProfile("sRGB")
            if pil_img.mode == "RGBA":
                alpha = pil_img.split()[3]
                rgb_part = pil_img.convert("RGB")
                converted = ImageCms.profileToProfile(
                    rgb_part, src_profile, srgb_profile, outputMode="RGB"
                )
                converted.putalpha(alpha)
                pil_img = converted
            else:
                pil_img = ImageCms.profileToProfile(
                    pil_img, src_profile, srgb_profile, outputMode="RGB"
                )
        except Exception:
            if pil_img.mode == "CMYK":
                pil_img = pil_img.convert("RGB")
    elif pil_img.mode == "CMYK":
        pil_img = pil_img.convert("RGB")

    return pil_img


def load_image_pillow(path):
    try:
        with Image.open(path) as raw:
            dpi = _sanitize_dpi(raw.info.get("dpi"))
            img = normalize_image_input(raw)
            img = img.copy()
            img.info["dpi"] = dpi
            return img, dpi
    except (FileNotFoundError, OSError, ValueError) as e:
        raise IOError(f"Erro ao carregar imagem: {e}") from e


def pil_to_cv2(pil_image):
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
    return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)


def cv2_to_pil(cv2_image):
    return Image.fromarray(cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB))


def pil_to_qimage(pil_img):
    """Efficiently convert PIL.Image to PySide6.QtGui.QImage."""
    from PySide6.QtGui import QImage

    if pil_img.mode == "1":
        img = pil_img.convert("L")
        data = img.tobytes("raw", "L")
        qimage = QImage(data, img.width, img.height, img.width, QImage.Format_Grayscale8)
        return qimage.copy()
    elif pil_img.mode == "L":
        data = pil_img.tobytes("raw", "L")
        qimage = QImage(data, pil_img.width, pil_img.height, pil_img.width, QImage.Format_Grayscale8)
        return qimage.copy()
    elif pil_img.mode == "RGBA":
        data = pil_img.tobytes("raw", "RGBA")
        qimage = QImage(data, pil_img.width, pil_img.height, pil_img.width * 4, QImage.Format_RGBA8888)
        return qimage.copy()
    else:
        img = pil_img.convert("RGB")
        data = img.tobytes("raw", "RGB")
        qimage = QImage(data, img.width, img.height, img.width * 3, QImage.Format_RGB888)
        return qimage.copy()


def normalize_dpi(pil_img, current_dpi, target_dpi=300):
    dpi_val = current_dpi[0] if isinstance(current_dpi, tuple) else current_dpi

    if dpi_val < target_dpi:
        scale_factor = target_dpi / dpi_val
        new_size = (int(pil_img.width * scale_factor), int(pil_img.height * scale_factor))
        return pil_img.resize(new_size, resample=Image.LANCZOS), target_dpi

    return pil_img, dpi_val


def process_transparency(pil_img, bg_color=(255, 255, 255)):
    if pil_img.mode == "LA":
        pil_img = pil_img.convert("RGBA")

    if pil_img.mode != "RGBA":
        return pil_img, None

    background = Image.new("RGB", pil_img.size, bg_color)
    background.paste(pil_img, mask=pil_img.split()[3])

    alpha = np.array(pil_img.split()[3])
    _, binary_mask = cv2.threshold(alpha, 127, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    cv2_background = cv2.cvtColor(np.array(background), cv2.COLOR_RGB2BGR)
    cv2.drawContours(cv2_background, contours, -1, (0, 0, 0), 1)

    result_pil = Image.fromarray(cv2.cvtColor(cv2_background, cv2.COLOR_BGR2RGB))
    mask_pil = Image.fromarray(binary_mask)
    return result_pil, mask_pil


def apply_brightness_contrast(cv2_img, brightness=50, contrast=50):
    adj_b = brightness - 50
    adj_c = contrast - 50
    beta = adj_b * 2.55
    alpha = 1.0 + adj_c / 50.0
    return cv2.convertScaleAbs(cv2_img, alpha=alpha, beta=beta)


def apply_channel_mixing(cv2_img, r_weight=0.6, g_weight=0.3, b_weight=0.1):
    b, g, r = cv2.split(cv2_img)
    mixed = (r * r_weight + g * g_weight + b * b_weight).astype(np.uint8)
    return mixed


def apply_clahe_gamma(gray_img, clip_limit=2.0, tile_size=8, gamma=1.2, gamma_active=True):
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    clahe_img = clahe.apply(gray_img)

    if gamma_active:
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
        clahe_img = cv2.LUT(clahe_img, table)

    return clahe_img


def apply_density_adjustment(gray_img, density=1):
    if density <= 1:
        return gray_img
    offset = int((density - 1) * 10)
    return cv2.subtract(gray_img, offset)


def apply_sharpening(gray_img, hp_sigma=1.5, usm_sigma=1.0, usm_amount=2.5):
    gray_f = gray_img.astype(np.float32)

    blurred = cv2.GaussianBlur(gray_f, (0, 0), hp_sigma)
    high_pass = gray_f - blurred
    sharpened1 = np.clip(gray_f + high_pass, 0.0, 255.0)

    blurred_usm = cv2.GaussianBlur(sharpened1, (0, 0), usm_sigma)
    sharpened_final = sharpened1 + usm_amount * (sharpened1 - blurred_usm)

    return np.clip(np.rint(sharpened_final), 0.0, 255.0).astype(np.uint8)


def apply_dithering(pil_img, method="Atkinson"):
    if method == "Floyd-Steinberg":
        return pil_img.convert("1", dither=Image.FLOYDSTEINBERG)
    elif method == "Atkinson":
        return dither_atkinson(pil_img)
    elif method == "Jarvis-Judice-Ninke":
        return dither_jarvis(pil_img)
    return dither_atkinson(pil_img)


def apply_invert(pil_img):
    if pil_img.mode == "1":
        return ImageChops.invert(pil_img.convert("L")).convert("1")
    if pil_img.mode == "L":
        return ImageChops.invert(pil_img)
    return ImageChops.invert(pil_img.convert("RGB"))


def process_live_preview(pil_img, settings, preview_mode=False):
    current_dpi = settings.get("current_dpi", (72, 72))
    target_dpi = settings.get("target_dpi", 300)
    keep_native_resolution = settings.get("keep_native_resolution", False)
    width_mm = settings.get("width_mm", 0)
    height_mm = settings.get("height_mm", 0)
    background = settings.get("background", "Branco")
    brightness = settings.get("brightness", 50)
    contrast = settings.get("contrast", 50)
    gamma_active = settings.get("gamma_active", True)
    sharpen = settings.get("sharpen", 85)
    dither_method = settings.get("dither_method", "Atkinson")
    invert_colors = settings.get("invert_colors", False)
    density = settings.get("density", 1)

    bg_color = (0, 0, 0) if background == "Preto" else (255, 255, 255)

    if not preview_mode and not keep_native_resolution:
        if width_mm > 0 and height_mm > 0:
            target_w = max(1, round(width_mm / 25.4 * target_dpi))
            target_h = max(1, round(height_mm / 25.4 * target_dpi))
            # Redimensiona para a resolução final do laser ANTES de CLAHE/Sharpen/Dither
            # para calibrar o raio de nitidez aos pixels finais e igualar Preview == Exportação.
            if pil_img.size != (target_w, target_h):
                pil_img = pil_img.resize((target_w, target_h), resample=Image.LANCZOS)
        else:
            pil_img, _actual_dpi = normalize_dpi(pil_img, current_dpi, target_dpi=target_dpi)

    pil_img, bg_mask = process_transparency(pil_img, bg_color=bg_color)

    cv2_img = pil_to_cv2(pil_img)
    cv2_img = apply_brightness_contrast(cv2_img, brightness=brightness, contrast=contrast)
    gray_img = apply_channel_mixing(cv2_img)
    gray_img = apply_clahe_gamma(gray_img, gamma_active=gamma_active)
    gray_img = apply_density_adjustment(gray_img, density=density)

    usm_amount = (sharpen / 100.0) * 3.0
    gray_img = apply_sharpening(gray_img, usm_amount=usm_amount)

    pil_result = Image.fromarray(gray_img)

    pil_result = apply_dithering(pil_result, method=dither_method)

    if invert_colors:
        pil_result = apply_invert(pil_result)

    if bg_mask is not None:
        mode = pil_result.mode
        clean_val = 0 if background == "Preto" else 255
        clean_bg = Image.new(mode, pil_result.size, clean_val)
        if bg_mask.size != pil_result.size:
            bg_mask = bg_mask.resize(pil_result.size, Image.NEAREST)
        pil_result = Image.composite(pil_result, clean_bg, bg_mask)

    return pil_result
