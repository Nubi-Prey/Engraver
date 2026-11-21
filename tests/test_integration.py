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


def test_app_controller_pre_dither_instant_toggle_and_factory_presets(qapp, tmp_path):
    window = MainWindow()
    controller = AppController(window)

    # Presets de fábrica carregados no topo da sidebar, com "Fotorealista" selecionado por padrão
    combo_items = [window.sidebar.combo_presets.itemText(i) for i in range(window.sidebar.combo_presets.count())]
    assert combo_items[:3] == [
        "Padrão",
        "Minimalista",
        "Fotorealista",
    ]
    assert window.sidebar.combo_presets.currentText() == "Fotorealista"

    # Carrega imagem e roda preview com buffer duplo
    img_path = tmp_path / "sample.png"
    Image.new("RGB", (120, 120), (160, 120, 90)).save(img_path, dpi=(300, 300))
    controller.load_image(str(img_path))
    controller.debounce_timer.stop()
    controller._run_preview()
    controller.thread_pool.waitForDone(5000)
    qapp.processEvents()

    assert controller._last_dither_qimg is not None
    assert controller._last_pre_dither_qimg is not None
    assert window.viewer.lbl_sim_status.text() == "Simulação atualizada"

    # Alternar para Pré-Dithering deve atualizar instantaneamente sem disparar novo worker
    gen_before = controller.preview_generation
    window.viewer.btn_toggle_view.setChecked(True)
    assert controller.preview_generation == gen_before
    assert window.viewer.lbl_sim_status.text() == "Pré-dithering (Cinza)"

    # Alternar de volta para 1-bit
    window.viewer.btn_toggle_view.setChecked(False)
    assert controller.preview_generation == gen_before
    assert window.viewer.lbl_sim_status.text() == "Simulação atualizada"
    controller.cleanup()


def test_preview_export_100_percent_bit_identical_above_2400px(qapp, tmp_path):
    import numpy as np

    window = MainWindow()
    controller = AppController(window)

    # Cria imagem gradiente RGB e configura saída > 2400 px (100x60 mm @ 700 DPI = 2756x1654 px)
    grad = np.tile(np.linspace(10, 245, 300, dtype=np.uint8), (180, 1))
    rgb = np.stack([grad, np.roll(grad, 30, axis=1), np.flip(grad, axis=1)], axis=-1)
    src_path = tmp_path / "high_dpi_src.png"
    Image.fromarray(rgb, mode="RGB").save(src_path, dpi=(300, 300))

    controller.load_image(str(src_path))
    controller.debounce_timer.stop()
    window.sidebar.apply_preset_settings(controller.presets_mgr.get_preset("Fotorealista"))
    window.sidebar.aspect_lock.set_dimensions(100.0, 60.0)
    window.sidebar.slider_dpi.setValue(700)
    controller.debounce_timer.stop()

    controller._run_preview()
    controller.thread_pool.waitForDone(10000)
    qapp.processEvents()

    expected_w = round(100.0 / 25.4 * 700)
    expected_h = round(60.0 / 25.4 * 700)
    assert expected_w > 2400
    assert controller._last_dither_pil is not None
    assert controller._last_dither_pil.size == (expected_w, expected_h)

    settings = window.sidebar.get_all_settings()
    settings["current_dpi"] = controller.original_dpi

    # 1. Exportação reaproveitando o cache do preview
    out_cached = str(tmp_path / "export_cached.bmp")
    w_cached = ExportWorker(controller.original_pil, settings, out_cached, cached_pil=controller._last_dither_pil)
    w_cached.run()

    # 2. Exportação recalculada do zero (sem cache)
    out_fresh = str(tmp_path / "export_fresh.bmp")
    w_fresh = ExportWorker(controller.original_pil, settings, out_fresh, cached_pil=None)
    w_fresh.run()

    preview_arr = np.array(controller._last_dither_pil.convert("L"), dtype=np.uint8)
    with Image.open(out_cached) as img_c, Image.open(out_fresh) as img_f:
        assert img_c.mode == "1"
        assert img_f.mode == "1"
        assert img_c.size == (expected_w, expected_h)
        assert abs(img_c.info["dpi"][0] - 700.0) <= 1.0
        assert np.array_equal(preview_arr, np.array(img_c.convert("L"), dtype=np.uint8))
        assert np.array_equal(preview_arr, np.array(img_f.convert("L"), dtype=np.uint8))

    # Valida single-flight coalescing: não dispara segundo worker se um já está ativo
    controller._preview_in_flight = True
    gen_start = controller.preview_generation
    controller._run_preview()
    assert controller._preview_dirty is True
    assert controller.preview_generation == gen_start + 1
    controller._preview_in_flight = False
    controller._preview_dirty = False

    controller.cleanup()
