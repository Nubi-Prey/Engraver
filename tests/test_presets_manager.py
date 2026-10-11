import os
import tempfile
import pytest
from core.presets_manager import PresetsManager


@pytest.fixture
def temp_presets_file():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    if os.path.exists(path):
        os.remove(path)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_default_presets_init(temp_presets_file):
    pm = PresetsManager(temp_presets_file)
    assert os.path.exists(temp_presets_file)
    presets = pm.list_presets()
    assert "Padrão" in presets
    default_data = pm.get_preset("Padrão")
    assert default_data["target_dpi"] == 300
    assert default_data["brightness"] == 50
    assert default_data["contrast"] == 50


def test_save_and_get_preset(temp_presets_file):
    pm = PresetsManager(temp_presets_file)
    custom = {
        "brightness": 75,
        "contrast": 60,
        "sharpen": 95,
        "dither_method": "Atkinson",
        "random_extra_key": "should_be_ignored"
    }
    saved = pm.save_preset("Ouro 18k", custom)
    assert saved is True
    assert "Ouro 18k" in pm.list_presets()

    loaded = pm.get_preset("Ouro 18k")
    assert loaded["brightness"] == 75
    assert loaded["contrast"] == 60
    assert loaded["sharpen"] == 95
    assert loaded["dither_method"] == "Atkinson"
    assert "random_extra_key" not in loaded


def test_update_existing_preset(temp_presets_file):
    pm = PresetsManager(temp_presets_file)
    pm.save_preset("Perfil A", {"brightness": 40})
    assert pm.get_preset("Perfil A")["brightness"] == 40

    pm.save_preset("Perfil A", {"brightness": 80})
    assert pm.get_preset("Perfil A")["brightness"] == 80


def test_delete_preset(temp_presets_file):
    pm = PresetsManager(temp_presets_file)
    pm.save_preset("Para Deletar", {"brightness": 10})
    assert "Para Deletar" in pm.list_presets()

    deleted = pm.delete_preset("Para Deletar")
    assert deleted is True
    assert "Para Deletar" not in pm.list_presets()


def test_cannot_delete_default_preset(temp_presets_file):
    pm = PresetsManager(temp_presets_file)
    deleted = pm.delete_preset("Padrão")
    assert deleted is False
    assert "Padrão" in pm.list_presets()


def test_empty_name_save(temp_presets_file):
    pm = PresetsManager(temp_presets_file)
    saved = pm.save_preset("   ", {"brightness": 50})
    assert saved is False


def test_corrupt_json_file(temp_presets_file):
    with open(temp_presets_file, "w") as f:
        f.write("{invalid json file...")
    pm = PresetsManager(temp_presets_file)
    assert "Padrão" in pm.list_presets()
