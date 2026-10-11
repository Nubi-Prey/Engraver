import os
import tempfile
import numpy as np
import pytest
from PIL import Image
from PySide6.QtGui import QImage
import engine


def test_load_image_pillow(sample_rgb_image):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        sample_rgb_image.save(tmp.name, dpi=(150, 150))
        tmp_path = tmp.name

    try:
        img, dpi = engine.load_image_pillow(tmp_path)
        assert img.size == (100, 100)
        assert round(dpi[0]) == 150
        assert round(dpi[1]) == 150
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_load_image_pillow_missing():
    with pytest.raises(Exception, match="Erro ao carregar imagem"):
        engine.load_image_pillow("/path/to/non_existent_file_xyz.png")


def test_pil_to_cv2_and_cv2_to_pil(sample_rgb_image):
    cv2_img = engine.pil_to_cv2(sample_rgb_image)
    assert cv2_img.shape == (100, 100, 3)
    back_to_pil = engine.cv2_to_pil(cv2_img)
    assert back_to_pil.size == (100, 100)
    assert back_to_pil.mode == "RGB"


def test_pil_to_qimage_modes(qapp, sample_rgb_image, sample_rgba_image):
    # RGB
    qimg_rgb = engine.pil_to_qimage(sample_rgb_image)
    assert isinstance(qimg_rgb, QImage)
    assert qimg_rgb.width() == 100
    assert qimg_rgb.height() == 100

    # RGBA
    qimg_rgba = engine.pil_to_qimage(sample_rgba_image)
    assert isinstance(qimg_rgba, QImage)
    assert qimg_rgba.width() == 100
    assert qimg_rgba.height() == 100

    # Grayscale
    gray = sample_rgb_image.convert("L")
    qimg_l = engine.pil_to_qimage(gray)
    assert isinstance(qimg_l, QImage)
    assert qimg_l.width() == 100

    # 1-bit
    bw = gray.convert("1")
    qimg_1 = engine.pil_to_qimage(bw)
    assert isinstance(qimg_1, QImage)
    assert qimg_1.width() == 100


def test_normalize_dpi():
    img = Image.new("RGB", (100, 100))
    # DPI 72 -> Target 300 should scale up by 300/72 (~4.166x)
    upscaled, dpi = engine.normalize_dpi(img, (72, 72), target_dpi=300)
    assert dpi == 300
    assert upscaled.width == int(100 * 300 / 72)
    assert upscaled.height == int(100 * 300 / 72)

    # DPI 300 -> Target 300 should NOT resize
    no_change, dpi2 = engine.normalize_dpi(img, (300, 300), target_dpi=300)
    assert dpi2 == 300
    assert no_change.size == (100, 100)


def test_process_transparency_rgba(sample_rgba_image):
    # With Black background
    res_black, mask = engine.process_transparency(sample_rgba_image, bg_color=(0, 0, 0))
    assert res_black.size == sample_rgba_image.size
    assert mask is not None
    assert mask.size == sample_rgba_image.size

    # With White background
    res_white, mask_w = engine.process_transparency(sample_rgba_image, bg_color=(255, 255, 255))
    assert res_white.size == sample_rgba_image.size
    assert mask_w is not None


def test_process_transparency_rgb_passthrough(sample_rgb_image):
    res, mask = engine.process_transparency(sample_rgb_image)
    assert res == sample_rgb_image
    assert mask is None


def test_apply_brightness_contrast():
    arr = np.full((50, 50, 3), 100, dtype=np.uint8)
    # Neutral: 50, 50 -> should be identical
    neutral = engine.apply_brightness_contrast(arr, brightness=50, contrast=50)
    assert np.all(neutral == 100)

    # Brighter
    brighter = engine.apply_brightness_contrast(arr, brightness=70, contrast=50)
    assert np.all(brighter > 100)


def test_apply_channel_mixing():
    # Pure red image
    red_arr = np.zeros((50, 50, 3), dtype=np.uint8)
    red_arr[:, :, 2] = 200 # OpenCV BGR -> index 2 is R
    gray = engine.apply_channel_mixing(red_arr, r_weight=0.6, g_weight=0.3, b_weight=0.1)
    # 200 * 0.6 = 120
    assert np.all(gray == 120)


def test_apply_dithering_methods(sample_rgb_image):
    for method in ["Floyd-Steinberg", "Atkinson", "Jarvis-Judice-Ninke"]:
        res = engine.apply_dithering(sample_rgb_image, method=method)
        assert res.size == sample_rgb_image.size
        assert res.mode == "1"


def test_apply_invert():
    img_1 = Image.new("1", (20, 20), 0)
    inv_1 = engine.apply_invert(img_1)
    assert np.all(np.array(inv_1.convert("L")) == 255)

    img_rgb = Image.new("RGB", (20, 20), (0, 100, 255))
    inv_rgb = engine.apply_invert(img_rgb)
    assert inv_rgb.getpixel((0, 0)) == (255, 155, 0)


def test_process_live_preview_end_to_end(sample_rgb_image, default_settings):
    # Preview mode: preserves size
    res_preview = engine.process_live_preview(sample_rgb_image, default_settings, preview_mode=True)
    assert res_preview.size == sample_rgb_image.size
    assert res_preview.mode == "1"

    # Full export mode: scales to width_mm/height_mm @ target_dpi
    # 15mm / 25.4 * 300 = 177 px; 20mm / 25.4 * 300 = 236 px
    res_export = engine.process_live_preview(sample_rgb_image, default_settings, preview_mode=False)
    expected_w = round(15.0 / 25.4 * 300)
    expected_h = round(20.0 / 25.4 * 300)
    assert res_export.size == (expected_w, expected_h)
    assert res_export.mode == "1"
