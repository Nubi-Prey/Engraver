import numpy as np
from PIL import Image
from core.dither_backend import dither_atkinson, dither_jarvis, dither_halftone_clustered


def test_dither_atkinson_output_properties():
    img = Image.new("L", (80, 60), 128)
    out = dither_atkinson(img)
    assert out.size == (80, 60)
    assert out.mode == "1"

    # Verify only binary values (0 or 255) when in L mode
    arr = np.array(out.convert("L"), dtype=np.uint8)
    unique_vals = set(np.unique(arr))
    assert unique_vals.issubset({0, 255})


def test_dither_jarvis_output_properties():
    img = Image.new("L", (80, 60), 128)
    out = dither_jarvis(img)
    assert out.size == (80, 60)
    assert out.mode == "1"

    arr = np.array(out.convert("L"), dtype=np.uint8)
    unique_vals = set(np.unique(arr))
    assert unique_vals.issubset({0, 255})


def test_dither_all_white_and_all_black():
    white_img = Image.new("L", (30, 30), 255)
    out_white_atk = dither_atkinson(white_img)
    assert np.all(np.array(out_white_atk.convert("L")) == 255)

    black_img = Image.new("L", (30, 30), 0)
    out_black_atk = dither_atkinson(black_img)
    assert np.all(np.array(out_black_atk.convert("L")) == 0)

    out_white_jarvis = dither_jarvis(white_img)
    assert np.all(np.array(out_white_jarvis.convert("L")) == 255)

    out_black_jarvis = dither_jarvis(black_img)
    assert np.all(np.array(out_black_jarvis.convert("L")) == 0)


def test_dither_small_dimensions():
    for dim in [(1, 1), (2, 2), (3, 3), (5, 5)]:
        small_img = Image.new("L", dim, 128)
        atk_res = dither_atkinson(small_img)
        assert atk_res.size == dim
        jarvis_res = dither_jarvis(small_img)
        assert jarvis_res.size == dim
        ht_res = dither_halftone_clustered(small_img, cell_size=6)
        assert ht_res.size == dim


def test_dither_halftone_clustered_properties():
    # Cinza médio 128 -> distribuição equilibrada (~50% branco / 50% preto)
    mid_img = Image.new("L", (96, 96), 128)
    out = dither_halftone_clustered(mid_img, cell_size=6)
    assert out.size == (96, 96)
    assert out.mode == "1"
    arr = np.array(out.convert("L"), dtype=np.uint8)
    assert set(np.unique(arr)).issubset({0, 255})
    white_ratio = float((arr == 255).mean())
    assert 0.45 <= white_ratio <= 0.55

    # Extremos puros preservados
    white_out = np.array(dither_halftone_clustered(Image.new("L", (32, 32), 255)).convert("L"))
    black_out = np.array(dither_halftone_clustered(Image.new("L", (32, 32), 0)).convert("L"))
    assert np.all(white_out == 255)
    assert np.all(black_out == 0)
