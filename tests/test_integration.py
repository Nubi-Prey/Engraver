import os
import tempfile
import pytest
from PIL import Image
from views.main_window import MainWindow
from controllers.app_controller import AppController
from controllers.preview_worker import ExportWorker
import engine


@pytest.fixture
def temp_image_file(sample_rgb_image):
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    sample_rgb_image.save(path, dpi=(300, 300))
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_app_controller_full_workflow(qapp, temp_image_file):
    window = MainWindow()
    controller = AppController(window)

    # 1. Simular carregamento de imagem diretamente
    pil_img, dpi = engine.load_image_pillow(temp_image_file)
    controller.original_pil = pil_img
    controller.original_dpi = dpi
    w, h = pil_img.size
    controller.view.sidebar.aspect_lock.set_dimensions(15.0, 15.0)
    controller.view.viewer.set_original_image(engine.pil_to_qimage(pil_img), f"{w} x {h} px")

    # 2. Alterar configurações
    sb = controller.view.sidebar
    sb.slider_bright.setValue(70)
    sb.slider_contrast.setValue(60)
    sb.combo_method.setCurrentText("Atkinson")

    # 3. Executar o preview em background
    controller._run_preview()
    controller.thread_pool.waitForDone(5000)
    qapp.processEvents()

    assert controller.view.viewer.lbl_sim_status.text() == "Simulação atualizada"

    # 4. Salvar preset e verificar atualização da sidebar
    controller.presets_mgr.save_preset("Teste Integrado", sb.get_all_settings())
    presets_list = controller.presets_mgr.list_presets()
    assert "Teste Integrado" in presets_list
    sb.update_presets_list(presets_list, current="Teste Integrado")
    assert sb.combo_presets.currentText() == "Teste Integrado"

    # 5. Exportar em alta resolução
    with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as tmp_export:
        tmp_export_path = tmp_export.name

    try:
        settings = sb.get_all_settings()
        settings["current_dpi"] = dpi
        worker = ExportWorker(pil_img, settings, tmp_export_path)
        worker.run()
        assert os.path.exists(tmp_export_path)
        assert os.path.getsize(tmp_export_path) > 0

        # Verificar imagem exportada
        with Image.open(tmp_export_path) as exported_img:
            assert exported_img.mode == "1"
            expected_w = round(15.0 / 25.4 * settings["target_dpi"])
            assert exported_img.width == expected_w
    finally:
        if os.path.exists(tmp_export_path):
            os.remove(tmp_export_path)
        controller.presets_mgr.delete_preset("Teste Integrado")
