import cv2
import numpy as np
from PIL import Image, ImageChops
from PySide6.QtGui import QImage
from core.dither_backend import dither_atkinson, dither_jarvis


def load_image_pillow(path):
    try:
        with Image.open(path) as raw:
            dpi = raw.info.get("dpi", (72, 72))
            img = raw.copy()
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
    blurred = cv2.GaussianBlur(gray_img, (0, 0), hp_sigma)
    high_pass = cv2.subtract(gray_img, blurred)
    sharpened1 = cv2.add(gray_img, high_pass)

    blurred_usm = cv2.GaussianBlur(sharpened1, (0, 0), usm_sigma)
    sharpened_final = cv2.addWeighted(sharpened1, 1.0 + usm_amount, blurred_usm, -usm_amount, 0)

    return sharpened_final


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

    if not preview_mode:
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

    if not preview_mode and width_mm > 0 and height_mm > 0:
        target_w = round(width_mm / 25.4 * target_dpi)
        target_h = round(height_mm / 25.4 * target_dpi)
        if pil_result.size != (target_w, target_h):
            pil_result = pil_result.resize((target_w, target_h), Image.LANCZOS)
            if bg_mask is not None:
                bg_mask = bg_mask.resize((target_w, target_h), Image.NEAREST)

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
