import json
import os
import platform

DEFAULT_PRESET = {
    "target_dpi": 300,
    "brightness": 50,
    "contrast": 50,
    "gamma_active": True,
    "sharpen": 85,
    "background": "Preto",
    "dither_method": "Atkinson",
    "invert_colors": False,
    "density": 1,
}


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
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.presets = json.load(f)
            except Exception as e:
                print(f"[Engraver] Error loading presets: {e}")
                self.presets = {}

        if "Padrão" not in self.presets:
            self.presets["Padrão"] = DEFAULT_PRESET.copy()
            self.save()
        elif self.presets.get("Padrão", {}).get("dither_method") == "Floyd-Steinberg":
            self.presets["Padrão"]["dither_method"] = "Atkinson"
            self.save()

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.presets, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Engraver] Error saving presets: {e}")

    def list_presets(self):
        # Guarantee "Padrão" is always first
        keys = list(self.presets.keys())
        if "Padrão" in keys:
            keys.remove("Padrão")
            return ["Padrão"] + sorted(keys)
        return sorted(keys)

    def get_preset(self, name):
        return self.presets.get(name, DEFAULT_PRESET.copy())

    def save_preset(self, name, settings_dict):
        name = name.strip()
        if not name:
            return False
        # Strip non-preset keys (e.g. width_mm, height_mm, current_dpi)
        clean_preset = {}
        for k in DEFAULT_PRESET:
            if k in settings_dict:
                clean_preset[k] = settings_dict[k]
            else:
                clean_preset[k] = DEFAULT_PRESET[k]

        self.presets[name] = clean_preset
        self.save()
        return True

    def delete_preset(self, name):
        if name == "Padrão":
            return False # Factory preset cannot be deleted
        if name in self.presets:
            del self.presets[name]
            self.save()
            return True
        return False
