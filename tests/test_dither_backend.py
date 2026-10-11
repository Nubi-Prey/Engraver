import numpy as np
from PIL import Image
from core.dither_backend import dither_atkinson, dither_jarvis


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
