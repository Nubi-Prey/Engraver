import ctypes
import os
import platform
import subprocess
import numpy as np
from PIL import Image

import sys

def _get_core_dir():
    mod_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(os.path.join(mod_dir, "dither_accel.c")) or any(
        os.path.exists(os.path.join(mod_dir, f)) for f in ("dither_accel.so", "dither_accel.dll", "dither_accel.dylib")
    ):
        return mod_dir
    exe_core = os.path.join(os.path.dirname(sys.executable), "core")
    if os.path.exists(exe_core):
        return exe_core
    return mod_dir

_DIR = _get_core_dir()
_LIB = None


def _compile_c_lib():
    c_source = os.path.join(_DIR, "dither_accel.c")
    if not os.path.exists(c_source):
        return None

    system = platform.system()
    if system == "Windows":
        lib_name = "dither_accel.dll"
    elif system == "Darwin":
        lib_name = "dither_accel.dylib"
    else:
        lib_name = "dither_accel.so"

    lib_path = os.path.join(_DIR, lib_name)

    # Check if already compiled and up to date
    if os.path.exists(lib_path):
        if os.path.getmtime(lib_path) >= os.path.getmtime(c_source):
            return lib_path

    # Attempt compilation with gcc / clang
    compiler = "gcc"
    for comp in ["gcc", "clang"]:
        try:
            subprocess.run([comp, "--version"], capture_output=True, check=True)
            compiler = comp
            break
        except Exception:
            continue

    try:
        if system == "Windows":
            cmd = [compiler, "-O3", "-shared", "-o", lib_path, c_source]
        else:
            cmd = [compiler, "-O3", "-fPIC", "-shared", "-o", lib_path, c_source]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and os.path.exists(lib_path):
            return lib_path
    except Exception:
        pass

    return lib_path if os.path.exists(lib_path) else None


def _init_lib():
    global _LIB
    if _LIB is not None:
        return _LIB

    lib_path = _compile_c_lib()
    if lib_path and os.path.exists(lib_path):
        try:
            lib = ctypes.CDLL(lib_path)
            # void atkinson_dither(double *pixels, int width, int height)
            lib.atkinson_dither.argtypes = [
                ctypes.POINTER(ctypes.c_double),
                ctypes.c_int,
                ctypes.c_int,
            ]
            lib.atkinson_dither.restype = None

            # void jarvis_dither(double *pixels, int width, int height)
            lib.jarvis_dither.argtypes = [
                ctypes.POINTER(ctypes.c_double),
                ctypes.c_int,
                ctypes.c_int,
            ]
            lib.jarvis_dither.restype = None

            _LIB = lib
            return _LIB
        except Exception as e:
            print(f"[Engraver] Warning: Failed to load C dither library ({e}), using fallback.")
    return None


def dither_atkinson(pil_img):
    img = pil_img.convert("L")
    pixels = np.array(img, dtype=np.float64)
    h, w = pixels.shape

    lib = _init_lib()
    if lib is not None:
        c_ptr = pixels.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
        lib.atkinson_dither(c_ptr, w, h)
    else:
        # Fallback in Python
        for y in range(h):
            for x in range(w):
                old_val = pixels[y, x]
                new_val = 255.0 if old_val >= 128.0 else 0.0
                pixels[y, x] = new_val
                error = old_val - new_val
                e8 = error / 8.0
                if x + 1 < w:
                    pixels[y, x + 1] += e8
                if x + 2 < w:
                    pixels[y, x + 2] += e8
                if y + 1 < h:
                    if x - 1 >= 0:
                        pixels[y + 1, x - 1] += e8
                    pixels[y + 1, x] += e8
                    if x + 1 < w:
                        pixels[y + 1, x + 1] += e8
                if y + 2 < h:
                    pixels[y + 2, x] += e8

    result = np.where(pixels >= 128, 255, 0).astype(np.uint8)
    return Image.fromarray(result).convert("1")


def dither_jarvis(pil_img):
    img = pil_img.convert("L")
    pixels = np.array(img, dtype=np.float64)
    h, w = pixels.shape

    lib = _init_lib()
    if lib is not None:
        c_ptr = pixels.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
        lib.jarvis_dither(c_ptr, w, h)
    else:
        # Fallback in Python
        for y in range(h):
            for x in range(w):
                old_val = pixels[y, x]
                new_val = 255.0 if old_val >= 128.0 else 0.0
                pixels[y, x] = new_val
                error = old_val - new_val
                if x + 1 < w:
                    pixels[y, x + 1] += error * (7.0 / 48.0)
                if x + 2 < w:
                    pixels[y, x + 2] += error * (5.0 / 48.0)
                if y + 1 < h:
                    if x - 2 >= 0:
                        pixels[y + 1, x - 2] += error * (3.0 / 48.0)
                    if x - 1 >= 0:
                        pixels[y + 1, x - 1] += error * (5.0 / 48.0)
                    pixels[y + 1, x] += error * (7.0 / 48.0)
                    if x + 1 < w:
                        pixels[y + 1, x + 1] += error * (5.0 / 48.0)
                    if x + 2 < w:
                        pixels[y + 1, x + 2] += error * (3.0 / 48.0)
                if y + 2 < h:
                    if x - 2 >= 0:
                        pixels[y + 2, x - 2] += error * (1.0 / 48.0)
                    if x - 1 >= 0:
                        pixels[y + 2, x - 1] += error * (3.0 / 48.0)
                    pixels[y + 2, x] += error * (5.0 / 48.0)
                    if x + 1 < w:
                        pixels[y + 2, x + 1] += error * (3.0 / 48.0)
                    if x + 2 < w:
                        pixels[y + 2, x + 2] += error * (1.0 / 48.0)

    result = np.where(pixels >= 128, 255, 0).astype(np.uint8)
    return Image.fromarray(result).convert("1")
