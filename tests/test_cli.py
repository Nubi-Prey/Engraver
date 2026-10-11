import os
import tempfile
from PIL import Image
from cli import run_cli


def test_cli_basic_execution(sample_rgb_image):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_in:
        sample_rgb_image.save(tmp_in.name, dpi=(300, 300))
        in_path = tmp_in.name

    with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as tmp_out:
        out_path = tmp_out.name

    try:
        ret = run_cli([in_path, "-o", out_path, "-q"])
        assert ret == 0
        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 0

        # Output must be a valid 1-bit BMP
        with Image.open(out_path) as img:
            assert img.mode == "1"
            assert img.size == sample_rgb_image.size
    finally:
        if os.path.exists(in_path):
            os.remove(in_path)
        if os.path.exists(out_path):
            os.remove(out_path)


def test_cli_with_methods_and_custom_settings(sample_rgb_image):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_in:
        sample_rgb_image.save(tmp_in.name, dpi=(300, 300))
        in_path = tmp_in.name

    with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as tmp_out:
        out_path = tmp_out.name

    try:
        # Test with Atkinson method + brightness + contrast + density
        ret = run_cli([
            in_path,
            "-o", out_path,
            "-m", "Atkinson",
            "--brightness", "60",
            "--contrast", "55",
            "--density", "2",
            "--sharpen", "90",
            "-q"
        ])
        assert ret == 0
        assert os.path.exists(out_path)
        with Image.open(out_path) as img:
            assert img.mode == "1"
    finally:
        if os.path.exists(in_path):
            os.remove(in_path)
        if os.path.exists(out_path):
            os.remove(out_path)


def test_cli_legacy_flags_and_no_dither(sample_rgba_image):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_in:
        sample_rgba_image.save(tmp_in.name, dpi=(300, 300))
        in_path = tmp_in.name

    with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as tmp_out:
        out_path = tmp_out.name

    try:
        # Test with legacy --bg-black and --no-dither
        ret = run_cli([in_path, "-o", out_path, "--bg-black", "--no-dither", "-q"])
        assert ret == 0
        assert os.path.exists(out_path)
        with Image.open(out_path) as img:
            assert img.mode == "L" # Grayscale mode
    finally:
        if os.path.exists(in_path):
            os.remove(in_path)
        if os.path.exists(out_path):
            os.remove(out_path)


def test_cli_missing_file():
    ret = run_cli(["/path/to/non_existent_file_123.png", "-q"])
    assert ret == 1


def test_main_cli_dispatch(monkeypatch):
    import sys
    import main

    monkeypatch.setattr(sys, "argv", ["main.py", "cli", "--help"])
    exited = False
    exit_code = None

    def mock_exit(code=0):
        nonlocal exited, exit_code
        exited = True
        exit_code = code
        raise SystemExit(code)

    monkeypatch.setattr(sys, "exit", mock_exit)

    try:
        main.main()
    except SystemExit:
        pass

    assert exited is True
    assert exit_code == 0
