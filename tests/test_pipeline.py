import numpy as np
import pytest

from core.pipeline import (
    TRANSFORM_SPECS,
    default_transforms_config,
    get_transform_entry,
    normalize_transforms_config,
    run_transform_pipeline,
    transform_bilateral,
    transform_brightness_contrast,
    transform_channel_mixing,
    transform_clahe,
    transform_cleanup,
    transform_density,
    transform_gamma,
    transform_quantize,
    transform_sharpen,
    transform_tone_clamp,
)


def test_transform_brightness_contrast_neutral_and_adjusted():
    bgr = np.full((32, 32, 3), 100, dtype=np.uint8)
    assert np.array_equal(transform_brightness_contrast(bgr, 50, 50), bgr)
    brighter = transform_brightness_contrast(bgr, brightness=70, contrast=50)
    darker = transform_brightness_contrast(bgr, brightness=30, contrast=50)
    assert int(brighter.mean()) > 100
    assert int(darker.mean()) < 100


def test_transform_channel_mixing_weights_and_disable_bt601():
    # Imagem puramente vermelha em BGR -> canal index 2 = 200
    bgr = np.zeros((20, 20, 3), dtype=np.uint8)
    bgr[:, :, 2] = 200
    mixed = transform_channel_mixing(bgr, r_weight=0.6, g_weight=0.3, b_weight=0.1)
    assert np.all(mixed == 120)

    # Com channel_mixing desativado na pipeline, usa BT.601 (0.299 * 200 ≈ 60)
    cfg = default_transforms_config({
        "brightness_contrast": {"enabled": False},
        "channel_mixing": {"enabled": False},
        "clahe": {"enabled": False},
        "gamma": {"enabled": False},
        "sharpen": {"enabled": False},
    })
    bt601 = run_transform_pipeline(bgr, cfg)
    assert 58 <= int(bt601[0, 0]) <= 62


def test_transform_clahe_and_gamma_and_density():
    ramp = np.tile(np.linspace(80, 160, 64, dtype=np.uint8), (64, 1))
    clahed = transform_clahe(ramp, clip_limit=3.0, tile_size=8)
    assert int(clahed.max()) - int(clahed.min()) > int(ramp.max()) - int(ramp.min())

    assert np.array_equal(transform_gamma(ramp, gamma=1.0), ramp)
    assert float(transform_gamma(ramp, gamma=1.8).mean()) > float(ramp.mean())
    assert float(transform_gamma(ramp, gamma=0.6).mean()) < float(ramp.mean())

    assert np.array_equal(transform_density(ramp, level=1), ramp)
    dense = transform_density(ramp, level=4)
    assert np.all(dense == ramp - 30)


def test_transform_sharpen_real_bypass_without_high_pass():
    edge = np.full((64, 64), 90, dtype=np.uint8)
    edge[:, 32:] = 170

    # Bypass real: zero overshoot quando amount=0 e high_pass=False
    bypassed = transform_sharpen(edge, amount=0, high_pass=False)
    assert np.array_equal(bypassed, edge)

    # Com nitidez ativa: bordas ganham contraste local
    sharp = transform_sharpen(edge, amount=80, high_pass=True)
    assert sharp[:, 31].min() < 90
    assert sharp[:, 32].max() > 170


def test_transform_bilateral_smooths_noise_and_preserves_edge():
    rng = np.random.default_rng(42)
    base = np.full((64, 64), 80, dtype=np.int16)
    base[:, 32:] = 200
    noise = rng.integers(-12, 13, size=(64, 64), dtype=np.int16)
    noisy = np.clip(base + noise, 0, 255).astype(np.uint8)

    smoothed = transform_bilateral(noisy, passes=4, sigma=45)
    # Variância dentro do plano esquerdo deve cair significativamente
    assert float(smoothed[:, :26].std()) < float(noisy[:, :26].std()) * 0.5
    # Contraste da borda principal deve permanecer forte
    assert float(smoothed[:, 38:].mean()) - float(smoothed[:, :26].mean()) > 100.0


def test_transform_tone_clamp_cleans_near_white_and_near_black():
    img = np.array(
        [[0, 15, 20, 128, 240, 244, 255]],
        dtype=np.uint8,
    )
    clamped = transform_tone_clamp(img, black_clamp=20, white_clamp=240)
    assert clamped[0, 0] == 0
    assert clamped[0, 1] == 0
    assert clamped[0, 2] == 0
    assert clamped[0, 3] == 128
    assert clamped[0, 4] == 255
    assert clamped[0, 5] == 255
    assert clamped[0, 6] == 255

    # Caso extremo: black_clamp >= white_clamp não deve falhar
    safe = transform_tone_clamp(img, black_clamp=250, white_clamp=200)
    assert safe.shape == img.shape
    assert safe.dtype == np.uint8


def test_transform_quantize_hard_vs_soft_and_determinism():
    ramp = np.tile(np.arange(256, dtype=np.uint8), (32, 1))

    # 1. Hard quantization (softness=0, levels=4): determinístico e <= 4 valores únicos
    q_hard_1 = transform_quantize(ramp, levels=4, softness=0, mode="kmeans")
    q_hard_2 = transform_quantize(ramp, levels=4, softness=0, mode="kmeans")
    assert np.array_equal(q_hard_1, q_hard_2)
    uniq_hard = sorted(int(v) for v in np.unique(q_hard_1))
    assert len(uniq_hard) <= 4
    assert 0 in uniq_hard and 255 in uniq_hard
    for mid in uniq_hard:
        if mid not in (0, 255):
            assert 40 <= mid <= 215

    # 2. Soft quantization (softness=45): gera transição suave entre níveis preservando 0 e 255
    q_soft = transform_quantize(ramp, levels=4, softness=45, mode="kmeans")
    uniq_soft = np.unique(q_soft)
    assert len(uniq_soft) > 4
    assert q_soft[0, 0] == 0
    assert q_soft[0, 255] == 255

    # 3. Stencil 2 níveis (softness=0): apenas {0, 255}
    q_stencil = transform_quantize(ramp, levels=2, softness=0, mode="kmeans")
    assert set(int(v) for v in np.unique(q_stencil)).issubset({0, 255})

    # 4. Modo uniforme
    q_unif = transform_quantize(ramp, levels=4, softness=0, mode="uniform")
    assert set(int(v) for v in np.unique(q_unif)) == {0, 85, 170, 255}

    # 5. Imagens degeneradas (constantes) não falham
    for val in (0, 128, 255):
        const_img = np.full((16, 16), val, dtype=np.uint8)
        out = transform_quantize(const_img, levels=4, softness=35, mode="kmeans")
        assert out.shape == (16, 16)
        assert out.dtype == np.uint8


@pytest.mark.parametrize("method", ["morph_close_open", "median"])
@pytest.mark.parametrize("kernel_size", [3, 5])
def test_transform_cleanup_removes_isolated_speckles(method, kernel_size):
    img = np.full((32, 32), 255, dtype=np.uint8)
    img[16, 16] = 0  # Ilha preta isolada de 1 px
    cleaned = transform_cleanup(img, method=method, kernel_size=kernel_size)
    assert cleaned[16, 16] == 255

    dark = np.zeros((32, 32), dtype=np.uint8)
    dark[16, 16] = 255  # Ilha branca isolada de 1 px
    cleaned_dark = transform_cleanup(dark, method=method, kernel_size=kernel_size)
    assert cleaned_dark[16, 16] == 0


def test_normalize_transforms_config_completeness_and_flat_compat():
    cfg_default = default_transforms_config()
    assert len(cfg_default) == len(TRANSFORM_SPECS)

    # Normalização a partir de dicionário plano (compat CLI)
    flat = {
        "clahe_enabled": False,
        "sharpen": 0,
        "white_clamp": 240,
        "black_clamp": 25,
        "quantize_levels": 4,
        "quantize_softness": 30,
        "bilateral_passes": 3,
        "cleanup_method": "median",
        "cleanup_kernel": 5,
    }
    norm = normalize_transforms_config(flat)
    assert get_transform_entry(norm, "clahe")["enabled"] is False
    assert get_transform_entry(norm, "sharpen")["enabled"] is False
    assert get_transform_entry(norm, "tone_clamp")["enabled"] is True
    assert get_transform_entry(norm, "tone_clamp")["params"]["white_clamp"] == 240
    assert get_transform_entry(norm, "quantize")["enabled"] is True
    assert get_transform_entry(norm, "quantize")["params"]["softness"] == 30
    assert get_transform_entry(norm, "cleanup")["enabled"] is True
    assert get_transform_entry(norm, "cleanup")["params"]["method"] == "median"
    assert get_transform_entry(norm, "cleanup")["params"]["kernel_size"] == 5
