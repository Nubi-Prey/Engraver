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


def test_safe_rational_loaders_patched():
    import math
    import struct
    from PIL import TiffImagePlugin

    dispatch = TiffImagePlugin.ImageFileDirectory_v2._load_dispatch
    assert dispatch[5][1] is engine._safe_load_rational
    assert dispatch[10][1] is engine._safe_load_signed_rational

    ifd = TiffImagePlugin.ImageFileDirectory_v2()
    # Unsigned rational: 300/1 and 0/0
    raw_u = struct.pack(">4L", 300, 1, 0, 0)
    ifd._endian = ">"
    assert engine._safe_load_rational(ifd, raw_u, legacy_api=True) == ((300, 1), (0, 0))
    res_u = engine._safe_load_rational(ifd, raw_u, legacy_api=False)
    assert res_u[0] == 300.0 and isinstance(res_u[0], float)
    assert math.isnan(res_u[1])

    # Signed rational: -150/2
    raw_s = struct.pack(">2l", -150, 2)
    assert engine._safe_load_signed_rational(ifd, raw_s, legacy_api=True) == ((-150, 2),)
    res_s = engine._safe_load_signed_rational(ifd, raw_s, legacy_api=False)
    assert res_s == (-75.0,) and isinstance(res_s[0], float)


def test_load_image_pillow_jpeg_with_exif_rational_dpi(tmp_path):
    from PIL import TiffImagePlugin

    # JPEG profissional com EXIF XResolution=300/1, YResolution=300/1, ResolutionUnit=2 (inch)
    exif_inch = Image.Exif()
    exif_inch[0x011A] = 300.0
    exif_inch[0x011B] = 300.0
    exif_inch[0x0128] = 2
    jpg_inch = tmp_path / "pro_inch.JPG"
    Image.new("RGB", (120, 80), (120, 80, 40)).save(jpg_inch, format="JPEG", exif=exif_inch)

    img, dpi = engine.load_image_pillow(str(jpg_inch))
    assert img.size == (120, 80)
    assert isinstance(dpi[0], float) and not isinstance(dpi[0], TiffImagePlugin.IFDRational)
    assert round(dpi[0]) == 300
    assert round(dpi[1]) == 300

    # JPEG com EXIF ResolutionUnit=3 (cm): 100 dpcm == 254 dpi
    exif_cm = Image.Exif()
    exif_cm[0x011A] = 100.0
    exif_cm[0x011B] = 100.0
    exif_cm[0x0128] = 3
    jpg_cm = tmp_path / "pro_cm.JPG"
    Image.new("RGB", (60, 60), (200, 100, 50)).save(jpg_cm, format="JPEG", exif=exif_cm)

    _, dpi_cm = engine.load_image_pillow(str(jpg_cm))
    assert round(dpi_cm[0]) == 254


def test_load_image_pillow_exif_orientation_transpose(tmp_path):
    exif = Image.Exif()
    exif[0x0112] = 6  # Rotate 90 CW -> 80x40 deve virar 40x80
    jpg_path = tmp_path / "rotated.JPG"
    Image.new("RGB", (80, 40), (10, 20, 30)).save(jpg_path, format="JPEG", exif=exif)

    img, _ = engine.load_image_pillow(str(jpg_path))
    assert img.size == (40, 80)


def test_normalize_image_input_modes_and_truncated_jpeg(tmp_path):
    from PIL import ImageCms

    # 1. CMYK -> RGB
    cmyk_img = Image.new("CMYK", (40, 40), (0, 255, 255, 0))
    norm_cmyk = engine.normalize_image_input(cmyk_img)
    assert norm_cmyk.mode == "RGB"

    # 2. 16-bit grayscale (I;16) -> L preservando faixa dinâmica
    arr16 = np.array([[0, 32768], [65535, 16384]], dtype=np.uint16)
    img16 = Image.fromarray(arr16)
    assert img16.mode == "I;16"
    norm16 = engine.normalize_image_input(img16)
    assert norm16.mode == "L"
    out_arr = np.array(norm16)
    assert out_arr[0, 0] == 0
    assert 120 <= out_arr[0, 1] <= 135
    assert out_arr[1, 0] == 255

    # 3. Paleta P com transparência -> RGBA
    pal = Image.new("P", (20, 20), 0)
    pal.info["transparency"] = 0
    norm_pal = engine.normalize_image_input(pal)
    assert norm_pal.mode == "RGBA"

    # 4. RGB com perfil ICC sRGB embutido
    srgb_bytes = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    icc_img = Image.new("RGB", (20, 20), (180, 90, 45))
    icc_img.info["icc_profile"] = srgb_bytes
    norm_icc = engine.normalize_image_input(icc_img)
    assert norm_icc.mode == "RGB"

    # 5. JPEG levemente truncado (sem marcador EOI FFD9)
    trunc_path = tmp_path / "truncated.jpeg"
    Image.new("RGB", (40, 40), (100, 150, 200)).save(trunc_path, format="JPEG")
    raw_bytes = trunc_path.read_bytes()
    assert raw_bytes.endswith(b"\xff\xd9")
    trunc_path.write_bytes(raw_bytes[:-2])
    loaded, _ = engine.load_image_pillow(str(trunc_path))
    assert loaded.size == (40, 40)


def test_process_live_preview_whatsapp_72dpi_avoids_blind_upscale(monkeypatch, default_settings):
    # Simula imagem do WhatsApp (1600x1066 @ 72 DPI) exportada para 100x66.6 mm @ 300 DPI (1181x787 px)
    wpp_img = Image.new("RGB", (1600, 1066), (140, 110, 90))
    settings = {
        **default_settings,
        "current_dpi": (72.0, 72.0),
        "target_dpi": 300,
        "width_mm": 100.0,
        "height_mm": 66.6,
    }

    def fail_if_called(*args, **kwargs):
        raise AssertionError("normalize_dpi não deve ser chamado quando width_mm/height_mm já definem o alvo")

    monkeypatch.setattr(engine, "normalize_dpi", fail_if_called)
    res = engine.process_live_preview(wpp_img, settings, preview_mode=False)
    assert res.size == (round(100.0 / 25.4 * 300), round(66.6 / 25.4 * 300))
    assert res.mode == "1"


def test_apply_sharpening_symmetric_signed_high_pass():
    # Imagem cinza uniforme (128) com metade mais escura (100) e metade mais clara (156)
    img = np.full((64, 64), 100, dtype=np.uint8)
    img[:, 32:] = 156
    sharp = engine.apply_sharpening(img, usm_amount=1.5)
    # Borda escura deve escurecer (< 100) e borda clara deve clarear (> 156), mantendo média balanceada
    assert sharp[:, 31].min() < 100
    assert sharp[:, 32].max() > 156
    assert abs(float(sharp.mean()) - float(img.mean())) < 2.0


def test_process_live_preview_keep_native_resolution(default_settings):
    native_img = Image.new("RGB", (640, 480), (140, 110, 90))
    settings = {
        **default_settings,
        "keep_native_resolution": True,
        "current_dpi": (72.0, 72.0),
        "target_dpi": 300,
        "width_mm": 20.0,
        "height_mm": 15.0,
    }
    res = engine.process_live_preview(native_img, settings, preview_mode=False)
    assert res.size == (640, 480)
    assert res.mode == "1"
