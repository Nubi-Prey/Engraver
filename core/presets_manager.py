from copy import deepcopy
import json
import os
import platform

from core.pipeline import default_transforms_config, normalize_transforms_config

PRESET_KEYS = (
    "target_dpi",
    "background",
    "dither_method",
    "halftone_cell",
    "invert_colors",
    "transforms",
)

DEPRECATED_FACTORY_PRESETS = (
    "Minimalista (Entrada IA)",
    "Minimalista (Foto Direta)",
    "Base Limpa",
)


def _make_preset(
    *,
    target_dpi=300,
    background="Branco",
    dither_method="Atkinson",
    halftone_cell=6,
    invert_colors=False,
    transform_overrides=None,
):
    return {
        "target_dpi": int(target_dpi),
        "background": background,
        "dither_method": dither_method,
        "halftone_cell": int(halftone_cell),
        "invert_colors": bool(invert_colors),
        "transforms": default_transforms_config(transform_overrides),
    }


DEFAULT_PRESET = _make_preset()

FACTORY_PRESETS = {
    "Padrão": _make_preset(
        background="Branco",
        dither_method="Atkinson",
        transform_overrides={
            "brightness_contrast": {"enabled": False},
            "channel_mixing": {"enabled": False},
            "clahe": {"enabled": False},
            "gamma": {"enabled": False},
            "density": {"enabled": False},
            "sharpen": {"enabled": False},
            "bilateral": {"enabled": False},
            "tone_clamp": {"enabled": False},
            "quantize": {"enabled": False},
            "cleanup": {"enabled": False},
        },
    ),
    "Minimalista": _make_preset(
        background="Branco",
        dither_method="Atkinson",
        transform_overrides={
            "brightness_contrast": {"enabled": True, "params": {"brightness": 50, "contrast": 50}},
            "channel_mixing": {"enabled": True, "params": {"r_weight": 0.6, "g_weight": 0.3, "b_weight": 0.1}},
            "clahe": {"enabled": False, "params": {"clip_limit": 2.0, "tile_size": 8}},
            "gamma": {"enabled": True, "params": {"gamma": 1.1}},
            "density": {"enabled": False, "params": {"level": 1}},
            "sharpen": {"enabled": False, "params": {"amount": 85, "high_pass": False}},
            "bilateral": {"enabled": False, "params": {"passes": 2, "sigma": 40}},
            "tone_clamp": {"enabled": True, "params": {"black_clamp": 62, "white_clamp": 242}},
            "quantize": {"enabled": False, "params": {"levels": 6, "softness": 35, "mode": "uniform"}},
            "cleanup": {"enabled": False, "params": {"method": "median", "kernel_size": 3}},
        },
    ),
    "Fotorealista": _make_preset(
        background="Branco",
        dither_method="Atkinson",
        transform_overrides={
            "brightness_contrast": {"enabled": True, "params": {"brightness": 60, "contrast": 50}},
            "channel_mixing": {"enabled": True, "params": {"r_weight": 0.6, "g_weight": 0.3, "b_weight": 0.1}},
            "clahe": {"enabled": True, "params": {"clip_limit": 1.3, "tile_size": 4}},
            "gamma": {"enabled": False, "params": {"gamma": 1.0}},
            "density": {"enabled": False, "params": {"level": 1}},
            "sharpen": {"enabled": True, "params": {"amount": 20, "high_pass": True}},
            "bilateral": {"enabled": True, "params": {"passes": 2, "sigma": 15}},
            "tone_clamp": {"enabled": False, "params": {"black_clamp": 20, "white_clamp": 240}},
            "quantize": {"enabled": False, "params": {"levels": 4, "softness": 35, "mode": "kmeans"}},
            "cleanup": {"enabled": False, "params": {"method": "median", "kernel_size": 3}},
        },
    ),
}

FACTORY_PRESET_NAMES = tuple(FACTORY_PRESETS.keys())
DEFAULT_STARTUP_PRESET = "Fotorealista"


def _normalize_preset(raw_dict):
    if not isinstance(raw_dict, dict):
        return deepcopy(DEFAULT_PRESET)

    clean = {
        "target_dpi": int(raw_dict.get("target_dpi", DEFAULT_PRESET["target_dpi"])),
        "background": raw_dict.get("background", DEFAULT_PRESET["background"]),
        "dither_method": raw_dict.get("dither_method", DEFAULT_PRESET["dither_method"]),
        "halftone_cell": int(raw_dict.get("halftone_cell", DEFAULT_PRESET["halftone_cell"])),
        "invert_colors": bool(raw_dict.get("invert_colors", DEFAULT_PRESET["invert_colors"])),
        "transforms": normalize_transforms_config(raw_dict),
    }
    return clean


def get_default_presets_path():
    system = platform.system()
    if system == "Windows":
        base_dir = os.environ.get("APPDATA", os.path.expanduser("~"))
        config_dir = os.path.join(base_dir, "Engraver")
    elif system == "Darwin":
        config_dir = os.path.expanduser("~/Library/Application Support/Engraver")
    else:
        config_dir = os.path.expanduser("~/.config/engraver")

    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "presets.json")


class PresetsManager:
    def __init__(self, filepath=None):
        self.filepath = filepath or get_default_presets_path()
        self.presets = {}
        self.load()

    def load(self):
        loaded_raw = {}
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        loaded_raw = data
            except Exception as e:
                print(f"[Engraver] Error loading presets: {e}")
                loaded_raw = {}

        self.presets = {}
        dirty = not os.path.exists(self.filepath)

        # Preserva presets customizados do usuário, descartando presets de fábrica descontinuados
        for name, raw_preset in loaded_raw.items():
            if name in DEPRECATED_FACTORY_PRESETS:
                dirty = True
                continue
            if name in FACTORY_PRESETS:
                continue
            self.presets[name] = _normalize_preset(raw_preset)

        # Sincroniza todos os presets de fábrica com suas definições atuais
        for factory_name, factory_data in FACTORY_PRESETS.items():
            fresh = deepcopy(factory_data)
            if loaded_raw.get(factory_name) != fresh:
                dirty = True
            self.presets[factory_name] = fresh

        if dirty:
            self.save()

    def save(self):
        try:
            parent_dir = os.path.dirname(self.filepath)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.presets, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Engraver] Error saving presets: {e}")

    @staticmethod
    def is_factory_preset(name):
        return name in FACTORY_PRESETS

    def list_presets(self):
        # Garante presets de fábrica primeiro, na ordem definida, seguidos dos customizados
        factory_order = [name for name in FACTORY_PRESET_NAMES if name in self.presets]
        custom = sorted(k for k in self.presets.keys() if k not in FACTORY_PRESETS)
        return factory_order + custom

    def get_preset(self, name):
        if name in self.presets:
            return deepcopy(_normalize_preset(self.presets[name]))
        return deepcopy(DEFAULT_PRESET)

    def save_preset(self, name, settings_dict):
        name = name.strip()
        if not name:
            return False
        self.presets[name] = _normalize_preset(settings_dict)
        self.save()
        return True

    def delete_preset(self, name):
        if name in FACTORY_PRESETS:
            return False  # Factory presets cannot be deleted
        if name in self.presets:
            del self.presets[name]
            self.save()
            return True
        return False
