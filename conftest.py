import os
import sys
import pytest
from PIL import Image

# Force headless Qt for offscreen test execution (crucial for CI and headless environments)
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Ensure root directory is in sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Create a singleton QApplication instance for all Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def sample_rgb_image():
    """Generate a simple 100x100 RGB image with gradient for testing."""
    img = Image.new("RGB", (100, 100), (128, 128, 128))
    # Add a white square in center
    for y in range(40, 60):
        for x in range(40, 60):
            img.putpixel((x, y), (255, 255, 255))
    return img


@pytest.fixture
def sample_rgba_image():
    """Generate a simple 100x100 RGBA image with transparent background."""
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    # Add a solid red circle
    for y in range(25, 75):
        for x in range(25, 75):
            if (x - 50)**2 + (y - 50)**2 <= 20**2:
                img.putpixel((x, y), (255, 0, 0, 255))
    return img


@pytest.fixture
def default_settings():
    return {
        "width_mm": 15.0,
        "height_mm": 20.0,
        "target_dpi": 300,
        "brightness": 50,
        "contrast": 50,
        "gamma_active": True,
        "sharpen": 85,
        "background": "Preto",
        "dither_method": "Atkinson",
        "invert_colors": False,
        "density": 1,
        "current_dpi": (72, 72)
    }
