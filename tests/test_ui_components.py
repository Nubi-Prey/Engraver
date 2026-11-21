from PySide6.QtGui import QImage
from views.components.slider_spinbox import SliderSpinBox
from views.components.aspect_ratio_lock import AspectRatioLock
from views.viewer.side_by_side import SideBySideViewer
import engine


def test_slider_spinbox_sync(qapp):
    widget = SliderSpinBox("BRILHO", min_val=0, max_val=100, default_val=50)

    # Initial state
    assert widget.value() == 50
    assert widget.slider.value() == 50

    # Change value via spinbox
    emitted_vals = []
    widget.valueChanged.connect(lambda v: emitted_vals.append(v))

    widget.setValue(75)
    assert widget.value() == 75
    assert widget.slider.value() == 75
    assert 75 in emitted_vals

    # Reset button restores default
    widget.reset()
    assert widget.value() == 50
    assert widget.slider.value() == 50


def test_aspect_ratio_lock_behavior(qapp):
    # Default 15.0 x 20.0 -> aspect ratio = 0.75
    lock = AspectRatioLock(default_w=15.0, default_h=20.0)
    assert lock.spin_w.value() == 15.0
    assert lock.spin_h.value() == 20.0
    assert lock._is_locked is True

    # When locked: Width -> 30.0 should make Height -> 30.0 / 0.75 = 40.0
    lock.spin_w.setValue(30.0)
    assert lock.spin_h.value() == 40.0

    # When locked: Height -> 10.0 should make Width -> 10.0 * 0.75 = 7.5
    lock.spin_h.setValue(10.0)
    assert lock.spin_w.value() == 7.5

    # Unlock
    lock.btn_lock.click()
    assert lock._is_locked is False

    # Changing width should NOT change height when unlocked
    lock.spin_w.setValue(50.0)
    assert lock.spin_h.value() == 10.0


def test_side_by_side_viewer_sync(qapp):
    viewer = SideBySideViewer()
    img = QImage(100, 100, QImage.Format_RGB888)
    img.fill(0xFF0000)

    viewer.set_original_image(img, "100 x 100 px")
    assert viewer.lbl_orig_dims.text() == "100 x 100 px"

    viewer.set_simulated_image(img, "Concluído")
    assert viewer.lbl_sim_status.text() == "Concluído"

    # Test zoom synchronization
    viewer.canvas_orig.set_zoom_absolute(2.5, notify=True)
    assert viewer.canvas_sim.current_zoom == 2.5
    assert viewer.lbl_zoom.text() == "250%"

    viewer.canvas_sim.set_zoom_absolute(1.0, notify=True)
    assert viewer.canvas_orig.current_zoom == 1.0
    assert viewer.lbl_zoom.text() == "100%"


def test_sidebar_tabs_and_footer_structure(qapp):
    from views.sidebar.settings_sidebar import SettingsSidebar
    sidebar = SettingsSidebar()

    # Verifica se existem exatamente 2 abas configuradas
    assert sidebar.tabs.count() == 2
    assert sidebar.tabs.tabText(0) == "🎨 Imagem"
    assert sidebar.tabs.tabText(1) == "⚡ Gravação"

    # Verifica se os componentes do rodapé fixo estão instanciados e acessíveis
    assert sidebar.btn_export is not None
    assert sidebar.btn_export.text() == "EXPORTAR IMAGEM"
    assert sidebar.lbl_res_out1 is not None
    assert sidebar.lbl_res_alert is not None


def test_canvas_scroll_normalization(qapp):
    from views.viewer.canvas_view import CanvasView
    c1 = CanvasView()
    c2 = CanvasView()

    img1 = QImage(200, 200, QImage.Format_RGB888)
    img1.fill(0xFFFFFF)
    c1.set_image(img1)

    img2 = QImage(200, 200, QImage.Format_RGB888)
    img2.fill(0x000000)
    c2.set_image(img2)

    # Test sync scroll from c1 to c2
    c2.sync_scroll_from(c1)
    assert c2._syncing_pan is False


def test_default_100mm_axis_in_app_controller(qapp, tmp_path):
    from views.main_window import MainWindow
    from controllers.app_controller import AppController
    from PIL import Image

    window = MainWindow()
    controller = AppController(window)

    # 1. Imagem Paisagem (200x100) -> maior eixo largura 100mm, altura 50mm
    landscape_path = str(tmp_path / "landscape.png")
    Image.new("RGB", (200, 100), (255, 0, 0)).save(landscape_path)

    # Simular on_open_file carregando a imagem
    pil_img, dpi = engine.load_image_pillow(landscape_path)
    controller.original_pil = pil_img
    controller.original_dpi = dpi
    w, h = pil_img.size
    if w >= h:
        width_mm = 100.0
        height_mm = round(100.0 * (h / w), 1) if w > 0 else 100.0
    else:
        height_mm = 100.0
        width_mm = round(100.0 * (w / h), 1) if h > 0 else 100.0

    controller.view.sidebar.aspect_lock.set_dimensions(width_mm, height_mm)
    assert controller.view.sidebar.aspect_lock.spin_w.value() == 100.0
    assert controller.view.sidebar.aspect_lock.spin_h.value() == 50.0

    # 2. Imagem Retrato (100x300) -> maior eixo altura 100mm, largura 33.3mm
    portrait_path = str(tmp_path / "portrait.png")
    Image.new("RGB", (100, 300), (0, 255, 0)).save(portrait_path)
    pil_img, dpi = engine.load_image_pillow(portrait_path)
    w, h = pil_img.size
    if w >= h:
        width_mm = 100.0
        height_mm = round(100.0 * (h / w), 1) if w > 0 else 100.0
    else:
        height_mm = 100.0
        width_mm = round(100.0 * (w / h), 1) if h > 0 else 100.0

    controller.view.sidebar.aspect_lock.set_dimensions(width_mm, height_mm)
    assert controller.view.sidebar.aspect_lock.spin_h.value() == 100.0
    assert controller.view.sidebar.aspect_lock.spin_w.value() == 33.3


def test_loading_spinner_behavior(qapp):
    from views.components.loading_spinner import LoadingSpinner
    spinner = LoadingSpinner(size=20)
    assert not spinner.isVisible()
    assert not spinner.is_spinning()

    spinner.start()
    assert spinner.isVisible()
    assert spinner.is_spinning()

    spinner.stop()
    assert not spinner.isVisible()
    assert not spinner.is_spinning()


def test_side_by_side_set_loading(qapp):
    viewer = SideBySideViewer()
    assert not viewer.spinner.is_spinning()

    viewer.set_loading(True, "Processando...")
    assert viewer.spinner.is_spinning()
    assert viewer.lbl_sim_status.text() == "Processando..."

    viewer.set_loading(False, "Pronto")
    assert not viewer.spinner.is_spinning()
    assert viewer.lbl_sim_status.text() == "Pronto"


def test_auto_extension_logic(tmp_path):
    import os
    from PIL import Image
    from controllers.preview_worker import ExportWorker

    img = Image.new("RGB", (50, 50), (255, 255, 255))
    settings = {
        "width_mm": 10.0,
        "height_mm": 10.0,
        "target_dpi": 300,
        "brightness": 50,
        "contrast": 50,
        "gamma_active": True,
        "sharpen": 85,
        "background": "Branco",
        "dither_method": "Floyd-Steinberg",
        "invert_colors": False,
        "density": 1,
        "current_dpi": (72, 72)
    }

    # Caminho fornecido sem extensão
    base_target = str(tmp_path / "meu_arquivo_sem_extensao")
    root, ext = os.path.splitext(base_target)
    if not ext:
        target_path = base_target + ".bmp"
    else:
        target_path = base_target

    assert target_path.endswith(".bmp")

    worker = ExportWorker(img, settings, target_path)
    worker.run()
    assert os.path.exists(target_path)
    assert os.path.getsize(target_path) > 0
    with Image.open(target_path) as saved:
        assert saved.format == "BMP"


def test_smooth_zoom_wheel(qapp):
    from views.viewer.canvas_view import CanvasView
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtCore import Qt, QPoint, QPointF

    canvas = CanvasView()
    canvas.set_zoom_absolute(1.0)
    assert canvas.current_zoom == 1.0

    # Simular 1 entalhe de scroll do mouse (120 unidades de ângulo)
    event = QWheelEvent(
        QPointF(50, 50),
        QPointF(50, 50),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.NoButton,
        Qt.NoModifier,
        Qt.ScrollUpdate,
        False,
    )
    canvas.wheelEvent(event)

    # O fator suave deve ser aproximadamente 1.05 (e não o antigo 1.15 agressivo)
    assert 1.045 <= canvas.current_zoom <= 1.055


def test_default_dither_method_is_atkinson(qapp):
    from core.presets_manager import PresetsManager
    from views.sidebar.settings_sidebar import SettingsSidebar

    pm = PresetsManager()
    assert pm.get_preset("Padrão")["dither_method"] == "Atkinson"

    sidebar = SettingsSidebar()
    assert sidebar.combo_method.currentText() == "Atkinson"
    assert sidebar.combo_method.itemText(0) == "Atkinson"


def test_forced_dark_palette_and_sidebar_background(qapp):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPalette
    from views.sidebar.settings_sidebar import SettingsSidebar
    import main

    palette = main._build_dark_palette(QPalette, QColor)
    assert palette.color(QPalette.ColorRole.Window).name() == "#0e0c15"
    assert palette.color(QPalette.ColorRole.Base).name() == "#171523"
    assert palette.color(QPalette.ColorRole.Text).name() == "#f8fafc"

    sidebar = SettingsSidebar()
    assert sidebar.testAttribute(Qt.WA_StyledBackground) is True


def test_transform_card_toggle_and_summary(qapp):
    from views.components.transform_card import TransformCard

    card = TransformCard("bilateral", "7. Suavização Bilateral", default_enabled=False)
    card.set_summary_fn(lambda: "3× • σ45")
    assert not card.is_enabled()
    assert not card.is_expanded()
    assert card.lbl_summary.text() == "OFF"

    changes = []
    card.changed.connect(lambda: changes.append(True))

    card.chk_enabled.setChecked(True)
    assert card.is_enabled()
    assert card.is_expanded()
    assert card.lbl_summary.text() == "3× • σ45"
    assert len(changes) == 1

    card.chk_enabled.setChecked(False)
    assert not card.is_enabled()
    assert not card.is_expanded()
    assert card.lbl_summary.text() == "OFF"
    assert len(changes) == 2


def test_sidebar_modular_cards_white_default_and_preset_application(qapp):
    from views.sidebar.settings_sidebar import SettingsSidebar
    from core.presets_manager import FACTORY_PRESETS
    from core.pipeline import get_transform_entry

    sidebar = SettingsSidebar()

    # Fundo padrão deve ser Branco
    assert sidebar.rb_bg_white.isChecked() is True
    assert sidebar.rb_bg_black.isChecked() is False

    # Todos os 10 módulos devem existir
    assert len(sidebar.transform_cards) == 10

    # Halftone disponível no combo e slider de célula só visível quando selecionado na Aba 2
    sidebar.tabs.setCurrentIndex(1)
    assert sidebar.combo_method.findText("Halftone (Clusters)") >= 0
    assert sidebar.slider_halftone_cell.isHidden() is True
    sidebar.combo_method.setCurrentText("Halftone (Clusters)")
    assert sidebar.slider_halftone_cell.isHidden() is False
    assert sidebar.slider_halftone_cell.isVisibleTo(sidebar) is True

    # Aplicar preset "Minimalista" emite settingsChanged exatamente uma vez
    emitted = []
    sidebar.settingsChanged.connect(lambda: emitted.append(True))
    sidebar.apply_preset_settings(FACTORY_PRESETS["Minimalista"])
    assert len(emitted) == 1

    settings = sidebar.get_all_settings()
    assert settings["background"] == "Branco"
    assert get_transform_entry(settings["transforms"], "clahe")["enabled"] is False
    assert get_transform_entry(settings["transforms"], "gamma")["enabled"] is True
    assert get_transform_entry(settings["transforms"], "tone_clamp")["enabled"] is True
    assert get_transform_entry(settings["transforms"], "tone_clamp")["params"]["black_clamp"] == 62
    assert get_transform_entry(settings["transforms"], "tone_clamp")["params"]["white_clamp"] == 242

    # Aplicar "Fotorealista" ativa CLAHE, Nitidez e Bilateral suave
    sidebar.apply_preset_settings(FACTORY_PRESETS["Fotorealista"])
    photo_settings = sidebar.get_all_settings()
    assert get_transform_entry(photo_settings["transforms"], "clahe")["enabled"] is True
    assert get_transform_entry(photo_settings["transforms"], "sharpen")["enabled"] is True
    assert get_transform_entry(photo_settings["transforms"], "bilateral")["enabled"] is True

    # Voltar para "Padrão" (base limpa) deve desligar todos os módulos
    sidebar.apply_preset_settings(FACTORY_PRESETS["Padrão"])
    clean_settings = sidebar.get_all_settings()
    assert all(not t["enabled"] for t in clean_settings["transforms"])


def test_viewer_pre_dither_toggle(qapp):
    viewer = SideBySideViewer()
    toggled_states = []
    viewer.previewStageToggled.connect(lambda state: toggled_states.append(state))

    assert not viewer.is_pre_dither_view()
    assert "DITHERING" in viewer.lbl_sim_title.text()

    viewer.btn_toggle_view.setChecked(True)
    assert viewer.is_pre_dither_view()
    assert "PRÉ-DITHERING" in viewer.lbl_sim_title.text()
    assert toggled_states == [True]

    viewer.btn_toggle_view.setChecked(False)
    assert not viewer.is_pre_dither_view()
    assert "DITHERING" in viewer.lbl_sim_title.text()
    assert toggled_states == [True, False]


def test_canvas_view_area_mipmaps_and_transformation_modes(qapp):
    import numpy as np
    from PIL import Image
    from PySide6.QtCore import Qt
    from views.viewer.canvas_view import CanvasView

    canvas = CanvasView(use_area_mipmaps=True)
    # Padrão xadrez 1-bit 256x256 construído via NumPy (rápido e seguro em Python 3.10/3.11/3.12)
    yy, xx = np.indices((256, 256))
    checker = np.where((xx + yy) % 2 == 0, 255, 0).astype(np.uint8)
    qimg = engine.pil_to_qimage(Image.fromarray(checker, mode="L"))

    canvas.set_image(qimg)

    # Zoom 1.0x (1:1 Pixel) e 1.5x -> pixel exato (FastTransformation, mipmap 0)
    canvas.set_zoom_absolute(1.0)
    assert canvas.pixmap_item.transformationMode() == Qt.FastTransformation
    assert canvas._active_mipmap_level == 0

    canvas.set_zoom_absolute(1.5)
    assert canvas.pixmap_item.transformationMode() == Qt.FastTransformation
    assert canvas._active_mipmap_level == 0

    # Zoom 0.25x -> SmoothTransformation + mipmap INTER_AREA nível 2 preservando geometria 256x256
    canvas.set_zoom_absolute(0.25)
    assert canvas.pixmap_item.transformationMode() == Qt.SmoothTransformation
    assert canvas._active_mipmap_level == 2
    rect = canvas.pixmap_item.sceneBoundingRect()
    assert abs(rect.width() - 256.0) < 0.5
    assert abs(rect.height() - 256.0) < 0.5

    # Retornar para 1:1 restaura full-res nítido
    canvas.zoom_1_to_1()
    assert canvas.pixmap_item.transformationMode() == Qt.FastTransformation
    assert canvas._active_mipmap_level == 0
