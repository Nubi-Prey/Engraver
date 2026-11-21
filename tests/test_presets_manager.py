import json
import os
import tempfile
import pytest

from core.pipeline import get_transform_entry
from core.presets_manager import (
    DEPRECATED_FACTORY_PRESETS,
    FACTORY_PRESET_NAMES,
    PresetsManager,
)


@pytest.fixture
def temp_presets_file():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    if os.path.exists(path):
        os.remove(path)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_default_factory_presets_init(temp_presets_file):
    pm = PresetsManager(temp_presets_file)
    assert os.path.exists(temp_presets_file)
    presets = pm.list_presets()

    # Os 3 presets de fábrica devem existir no topo da lista
    assert list(FACTORY_PRESET_NAMES) == ["Padrão", "Minimalista", "Fotorealista"]
    assert presets[: len(FACTORY_PRESET_NAMES)] == ["Padrão", "Minimalista", "Fotorealista"]

    for name in FACTORY_PRESET_NAMES:
        data = pm.get_preset(name)
        assert data["target_dpi"] == 300
        assert data["background"] == "Branco"
        assert data["dither_method"] == "Atkinson"
        assert isinstance(data["transforms"], list)
        assert len(data["transforms"]) == 10

    # Padrão deve ser uma base limpa (todas as 10 transformações desativadas)
    padrao = pm.get_preset("Padrão")
    assert all(not t["enabled"] for t in padrao["transforms"])

    # Minimalista: brilho/contraste, mixagem, gama 1.1 e trava de extremos (62/242) ON
    mini = pm.get_preset("Minimalista")
    assert get_transform_entry(mini["transforms"], "brightness_contrast")["enabled"] is True
    assert get_transform_entry(mini["transforms"], "channel_mixing")["enabled"] is True
    assert get_transform_entry(mini["transforms"], "clahe")["enabled"] is False
    assert get_transform_entry(mini["transforms"], "gamma")["enabled"] is True
    assert get_transform_entry(mini["transforms"], "gamma")["params"]["gamma"] == 1.1
    assert get_transform_entry(mini["transforms"], "sharpen")["enabled"] is False
    assert get_transform_entry(mini["transforms"], "tone_clamp")["enabled"] is True
    assert get_transform_entry(mini["transforms"], "tone_clamp")["params"]["black_clamp"] == 62
    assert get_transform_entry(mini["transforms"], "tone_clamp")["params"]["white_clamp"] == 242
    assert get_transform_entry(mini["transforms"], "quantize")["params"]["levels"] == 6
    assert get_transform_entry(mini["transforms"], "quantize")["params"]["mode"] == "uniform"
    assert get_transform_entry(mini["transforms"], "cleanup")["params"]["method"] == "median"

    # Fotorealista: brilho 60, mixagem, CLAHE (1.3 / 4), nitidez (20 + HP), bilateral (2 / 15) ON
    foto = pm.get_preset("Fotorealista")
    assert get_transform_entry(foto["transforms"], "brightness_contrast")["enabled"] is True
    assert get_transform_entry(foto["transforms"], "brightness_contrast")["params"]["brightness"] == 60
    assert get_transform_entry(foto["transforms"], "channel_mixing")["enabled"] is True
    assert get_transform_entry(foto["transforms"], "clahe")["enabled"] is True
    assert get_transform_entry(foto["transforms"], "clahe")["params"]["clip_limit"] == 1.3
    assert get_transform_entry(foto["transforms"], "clahe")["params"]["tile_size"] == 4
    assert get_transform_entry(foto["transforms"], "gamma")["enabled"] is False
    assert get_transform_entry(foto["transforms"], "sharpen")["enabled"] is True
    assert get_transform_entry(foto["transforms"], "sharpen")["params"]["amount"] == 20
    assert get_transform_entry(foto["transforms"], "sharpen")["params"]["high_pass"] is True
    assert get_transform_entry(foto["transforms"], "bilateral")["enabled"] is True
    assert get_transform_entry(foto["transforms"], "bilateral")["params"]["passes"] == 2
    assert get_transform_entry(foto["transforms"], "bilateral")["params"]["sigma"] == 15


def test_save_and_get_preset(temp_presets_file):
    pm = PresetsManager(temp_presets_file)
    custom = {
        "brightness": 75,
        "contrast": 60,
        "sharpen": 95,
        "dither_method": "Atkinson",
        "background": "Preto",
        "random_extra_key": "should_be_ignored",
    }
    saved = pm.save_preset("Ouro 18k", custom)
    assert saved is True
    assert "Ouro 18k" in pm.list_presets()

    loaded = pm.get_preset("Ouro 18k")
    bc = get_transform_entry(loaded["transforms"], "brightness_contrast")
    sh = get_transform_entry(loaded["transforms"], "sharpen")
    assert bc["params"]["brightness"] == 75
    assert bc["params"]["contrast"] == 60
    assert sh["params"]["amount"] == 95
    assert loaded["dither_method"] == "Atkinson"
    assert loaded["background"] == "Preto"
    assert "random_extra_key" not in loaded


def test_update_existing_preset(temp_presets_file):
    pm = PresetsManager(temp_presets_file)
    pm.save_preset("Perfil A", {"brightness": 40})
    assert get_transform_entry(pm.get_preset("Perfil A")["transforms"], "brightness_contrast")["params"]["brightness"] == 40

    pm.save_preset("Perfil A", {"brightness": 80})
    assert get_transform_entry(pm.get_preset("Perfil A")["transforms"], "brightness_contrast")["params"]["brightness"] == 80


def test_delete_preset(temp_presets_file):
    pm = PresetsManager(temp_presets_file)
    pm.save_preset("Para Deletar", {"brightness": 10})
    assert "Para Deletar" in pm.list_presets()

    deleted = pm.delete_preset("Para Deletar")
    assert deleted is True
    assert "Para Deletar" not in pm.list_presets()


def test_cannot_delete_factory_presets(temp_presets_file):
    pm = PresetsManager(temp_presets_file)
    for factory_name in FACTORY_PRESET_NAMES:
        assert pm.is_factory_preset(factory_name) is True
        assert pm.delete_preset(factory_name) is False
        assert factory_name in pm.list_presets()


def test_legacy_json_and_deprecated_factory_presets_cleanup(temp_presets_file):
    legacy = {
        "Padrão": {
            "target_dpi": 300,
            "brightness": 50,
            "contrast": 50,
            "gamma_active": True,
            "sharpen": 85,
            "background": "Preto",
            "dither_method": "Floyd-Steinberg",
            "invert_colors": False,
            "density": 1,
        },
        "Minimalista (Entrada IA)": {"target_dpi": 300},
        "Minimalista (Foto Direta)": {"target_dpi": 300},
        "Base Limpa": {"target_dpi": 300},
        "Meu Legado": {
            "target_dpi": 400,
            "brightness": 65,
            "contrast": 55,
            "gamma_active": False,
            "sharpen": 0,
            "background": "Branco",
            "dither_method": "Atkinson",
            "invert_colors": True,
            "density": 2,
        },
    }
    with open(temp_presets_file, "w", encoding="utf-8") as f:
        json.dump(legacy, f)

    pm = PresetsManager(temp_presets_file)
    names = pm.list_presets()

    # Presets de fábrica antigos devem ser removidos automaticamente
    for deprecated in DEPRECATED_FACTORY_PRESETS:
        assert deprecated not in names

    # Novos presets de fábrica sincronizados
    assert names[:3] == ["Padrão", "Minimalista", "Fotorealista"]
    assert all(not t["enabled"] for t in pm.get_preset("Padrão")["transforms"])

    # Preset customizado legado preservado e normalizado
    custom = pm.get_preset("Meu Legado")
    assert custom["target_dpi"] == 400
    assert custom["invert_colors"] is True
    assert get_transform_entry(custom["transforms"], "gamma")["enabled"] is False
    assert get_transform_entry(custom["transforms"], "sharpen")["enabled"] is False
    assert get_transform_entry(custom["transforms"], "brightness_contrast")["params"]["brightness"] == 65


def test_empty_name_save(temp_presets_file):
    pm = PresetsManager(temp_presets_file)
    saved = pm.save_preset("   ", {"brightness": 50})
    assert saved is False


def test_corrupt_json_file(temp_presets_file):
    with open(temp_presets_file, "w") as f:
        f.write("{invalid json file...")
    pm = PresetsManager(temp_presets_file)
    assert pm.list_presets() == ["Padrão", "Minimalista", "Fotorealista"]
