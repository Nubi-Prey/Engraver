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


def test_app_controller_load_exif_uppercase_jpg_and_effective_dpi_alert(qapp, tmp_path):
    from controllers.app_controller import IMAGE_FILE_FILTER

    # Filtro deve incluir maiúsculas (Linux case-sensitive) e .jfif (WhatsApp Web)
    for ext in ("*.JPG", "*.JPEG", "*.JFIF", "*.PNG", "*.TIFF"):
        assert ext in IMAGE_FILE_FILTER

    window = MainWindow()
    controller = AppController(window)

    # 1. Foto profissional .JPG com EXIF 300 DPI e alta resolução (1500x1000 -> ~381 DPI em 100mm)
    exif = Image.Exif()
    exif[0x011A] = 300.0
    exif[0x011B] = 300.0
    exif[0x0128] = 2
    pro_path = tmp_path / "studio_photo.JPG"
    Image.new("RGB", (1500, 1000), (160, 120, 90)).save(pro_path, format="JPEG", exif=exif)

    controller.load_image(str(pro_path))
    controller.debounce_timer.stop()
    controller._run_preview()
    controller.thread_pool.waitForDone(5000)
    qapp.processEvents()

    assert "@ 300 DPI" in window.sidebar.lbl_info_dims.text()
    assert "300.0" not in window.sidebar.lbl_info_dims.text()
    assert window.viewer.lbl_sim_status.text() == "Simulação atualizada"
    assert "Resolução adequada" in window.sidebar.lbl_res_alert.text()
    # Painel Original deve preservar seus 1500x1000 pixels nativos (não ser rebaixado para 1181x787)
    orig_pm = window.viewer.canvas_orig.pixmap_item.pixmap()
    assert (orig_pm.width(), orig_pm.height()) == (1500, 1000)

    # Ativar "Manter resolução original" deve desabilitar controles físicos e mostrar saída 1:1
    window.sidebar.chk_keep_native_res.setChecked(True)
    assert not window.sidebar.aspect_lock.isEnabled()
    assert not window.sidebar.slider_dpi.isEnabled()
    assert "1500x1000 px (Original 1:1)" in window.sidebar.lbl_res_out2.text()
    window.sidebar.chk_keep_native_res.setChecked(False)

    # 2. Foto amadora de baixa resolução (400x300 @ 72 DPI em 100mm -> ~102 DPI efetivo < 300 DPI alvo)
    amateur_path = tmp_path / "whatsapp_small.jpeg"
    Image.new("RGB", (400, 300), (120, 100, 80)).save(amateur_path, format="JPEG")

    controller.load_image(str(amateur_path))
    assert "prefira foto original" in window.sidebar.lbl_res_alert.text()
    controller.cleanup()
