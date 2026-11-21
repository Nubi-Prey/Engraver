import json
import os
from PIL import Image
from PySide6.QtCore import QObject, QTimer, QThreadPool
from PySide6.QtWidgets import QFileDialog, QMessageBox, QInputDialog

from views.main_window import MainWindow
from core.presets_manager import DEFAULT_STARTUP_PRESET, PresetsManager
from controllers.preview_worker import PreviewWorker, ExportWorker
import engine

ORIG_DISPLAY_MAX_PX = 4096
IMAGE_FILE_FILTER = (
    "Imagens (*.png *.PNG *.jpg *.JPG *.jpeg *.JPEG *.jfif *.JFIF "
    "*.bmp *.BMP *.tiff *.TIFF *.tif *.TIF *.gif *.GIF *.webp *.WEBP);;"
    "Todos os arquivos (*.*)"
)


class AppController(QObject):
    def __init__(self, main_window: MainWindow):
        super().__init__()
        self.view = main_window
        self.presets_mgr = PresetsManager()

        self.original_pil = None
        self.original_dpi = (72.0, 72.0)
        self.current_filepath = None
        self.current_filename = None
        self._pending_filepath = None
        self.preview_generation = 0
        self._preview_in_flight = False
        self._preview_dirty = False
        self._last_dither_pil = None
        self._last_preview_key = None
        self._last_dither_qimg = None
        self._last_pre_dither_qimg = None

        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._run_preview)

        self.thread_pool = QThreadPool.globalInstance()

        self._connect_signals()
        self._init_presets()

    def cleanup(self):
        """Para temporizadores e aguarda workers pendentes para encerramento gracioso."""
        try:
            self.debounce_timer.stop()
            if self.thread_pool.activeThreadCount() > 0:
                self.thread_pool.waitForDone(1000)
        except Exception:
            pass

    def _connect_signals(self):
        sb = self.view.sidebar
        sb.openFileClicked.connect(self.on_open_file)
        sb.exportClicked.connect(self.on_export_file)
        sb.settingsChanged.connect(self.on_settings_changed)
        sb.presetSelected.connect(self.on_preset_selected)
        sb.presetSaveClicked.connect(self.on_preset_save)
        sb.presetDeleteClicked.connect(self.on_preset_delete)
        self.view.viewer.previewStageToggled.connect(self.on_preview_stage_toggled)

    def _init_presets(self):
        presets = self.presets_mgr.list_presets()
        self.view.sidebar.update_presets_list(presets, current=DEFAULT_STARTUP_PRESET)
        self.view.sidebar.apply_preset_settings(self.presets_mgr.get_preset(DEFAULT_STARTUP_PRESET))

    def _make_preview_key(self, settings: dict):
        return (id(self.original_pil), json.dumps(settings, sort_keys=True, default=str))

    def on_open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self.view,
            "Selecionar Imagem",
            "",
            IMAGE_FILE_FILTER,
        )
        if not filepath:
            return

        # Desacopla a abertura da imagem da pilha do diálogo modal nativo (Qt/Shiboken6)
        self._pending_filepath = filepath
        QTimer.singleShot(0, self._load_pending_file)

    def _load_pending_file(self):
        filepath = self._pending_filepath
        self._pending_filepath = None
        if filepath:
            self.load_image(filepath)

    def load_image(self, filepath: str):
        try:
            pil_img, dpi = engine.load_image_pillow(filepath)
            self.original_pil = pil_img
            self.original_dpi = dpi
            self.current_filepath = filepath
            self.current_filename = os.path.basename(filepath)
            self._last_dither_pil = None
            self._last_preview_key = None
            self._last_dither_qimg = None
            self._last_pre_dither_qimg = None

            w, h = pil_img.size
            mp = (w * h) / 1_000_000
            raw_dpi = dpi[0] if isinstance(dpi, tuple) else dpi
            dpi_val = int(round(float(raw_dpi)))

            # Dimensão padrão com maior eixo em 100.0 mm (proporcional)
            if w >= h:
                width_mm = 100.0
                height_mm = round(100.0 * (h / w), 1) if w > 0 else 100.0
            else:
                height_mm = 100.0
                width_mm = round(100.0 * (w / h), 1) if h > 0 else 100.0

            filename = os.path.basename(filepath)
            self.view.sidebar.set_file_info(filename, f"{mp:.1f}", width_mm, height_mm, dpi_val)
            self.view.sidebar.aspect_lock.set_dimensions(width_mm, height_mm)

            # Preserva a resolução nativa da imagem original no visualizador (teto apenas para >4K)
            if max(w, h) > ORIG_DISPLAY_MAX_PX:
                ratio = ORIG_DISPLAY_MAX_PX / max(w, h)
                display_orig = pil_img.resize((max(1, int(w * ratio)), max(1, int(h * ratio))), Image.LANCZOS)
            else:
                display_orig = pil_img
            qimg = engine.pil_to_qimage(display_orig)
            self.view.viewer.set_original_image(qimg, f"{w} x {h} px")

            self.view.set_status(f"Carregado: {filename} ({w}x{h} px)")
            self.on_settings_changed()

        except Exception as e:
            QMessageBox.critical(self.view, "Erro ao Abrir Arquivo", str(e))

    def on_settings_changed(self):
        self._update_resolution_info()
        if self.original_pil is not None:
            self.debounce_timer.start(200)

    def _update_resolution_info(self):
        settings = self.view.sidebar.get_all_settings()
        keep_native = settings.get("keep_native_resolution", False)
        width_mm = settings["width_mm"]
        height_mm = settings["height_mm"]
        target_dpi = settings["target_dpi"]

        if keep_native and self.original_pil is not None:
            out_w, out_h = self.original_pil.size
            total_mp = (out_w * out_h) / 1_000_000
            out1 = f"Saída: {out_w}x{out_h} px | {total_mp:.2f} MP"
            if total_mp > 10:
                alert = "⚠ Resolução muito alta!"
                alert_color = "#ef4444"
            elif total_mp > 5:
                alert = "✓ Resolução nativa (alta definição)"
                alert_color = "#C084FC"
            else:
                alert = "✓ Resolução nativa preservada"
                alert_color = "#C084FC"
            out2 = f"Saída: {out_w}x{out_h} px (Original 1:1)"
            self.view.sidebar.set_resolution_alerts(out1, alert, alert_color, out2)
            return

        out_w = round(width_mm / 25.4 * target_dpi)
        out_h = round(height_mm / 25.4 * target_dpi)
        total_mp = (out_w * out_h) / 1_000_000

        out1 = f"Saída: {out_w}x{out_h} px | {total_mp:.2f} MP"

        effective_dpi = None
        if self.original_pil is not None and width_mm > 0 and height_mm > 0:
            orig_w, orig_h = self.original_pil.size
            effective_dpi = min(orig_w / (width_mm / 25.4), orig_h / (height_mm / 25.4))

        if total_mp > 10:
            alert = "⚠ Resolução muito alta!"
            alert_color = "#ef4444"
        elif effective_dpi is not None and effective_dpi < target_dpi * 0.85:
            alert = f"⚠ Origem ~{int(round(effective_dpi))} DPI — prefira foto original"
            alert_color = "#f59e0b"
        elif total_mp > 5:
            alert = "⚠ Resolução alta"
            alert_color = "#f59e0b"
        else:
            alert = "✓ Resolução adequada"
            alert_color = "#C084FC"

        out2 = f"Saída: {out_w}x{out_h} px @ {target_dpi} DPI"
        self.view.sidebar.set_resolution_alerts(out1, alert, alert_color, out2)

    def _run_preview(self):
        if self.original_pil is None:
            return

        # Single-flight coalescing: evita empilhar múltiplos workers pesados em resolução cheia
        if self._preview_in_flight:
            self._preview_dirty = True
            self.preview_generation += 1
            return

        self._preview_in_flight = True
        self._preview_dirty = False
        self.preview_generation += 1
        gen = self.preview_generation

        # Feedback visual imediato: ativa spinner animado e atualiza status
        self.view.viewer.set_loading(True, "Processando simulação...")
        self.view.sidebar.lbl_res_alert.setText("Processando simulação...")

        settings = self.view.sidebar.get_all_settings()
        settings["current_dpi"] = self.original_dpi
        preview_key = self._make_preview_key(settings)

        # Roda na resolução EXATA da exportação (sem PREVIEW_MAX_PX) para 100% de fidelidade
        worker = PreviewWorker(self.original_pil, settings, gen, preview_key=preview_key)
        worker.signals.finished.connect(self._on_preview_finished)
        worker.signals.error.connect(self._on_preview_error)

        self.thread_pool.start(worker)

    def _on_preview_finished(self, generation, preview_key, dither_pil, qimg_dither, qimg_pre_dither):
        self._preview_in_flight = False
        if generation == self.preview_generation:
            self._last_dither_pil = dither_pil
            self._last_preview_key = preview_key
            self._last_dither_qimg = qimg_dither
            self._last_pre_dither_qimg = qimg_pre_dither
            active_qimg = qimg_pre_dither if self.view.viewer.is_pre_dither_view() else qimg_dither
            # Sincroniza a geometria da cena do canvas original sem destruir seus pixels nativos
            self.view.viewer.canvas_orig.set_display_size(active_qimg.width(), active_qimg.height())
            status_lbl = "Pré-dithering (Cinza)" if self.view.viewer.is_pre_dither_view() else "Simulação atualizada"
            self.view.viewer.set_simulated_image(active_qimg, status_lbl)
            self._update_resolution_info()

        if self._preview_dirty:
            self._preview_dirty = False
            self._run_preview()

    def on_preview_stage_toggled(self, show_pre_dither: bool):
        active_qimg = self._last_pre_dither_qimg if show_pre_dither else self._last_dither_qimg
        if active_qimg is not None:
            status_lbl = "Pré-dithering (Cinza)" if show_pre_dither else "Simulação atualizada"
            self.view.viewer.set_simulated_image(active_qimg, status_lbl)

    def _on_preview_error(self, generation, error_msg):
        self._preview_in_flight = False
        if generation == self.preview_generation:
            self.view.viewer.set_loading(False, "Erro no processamento")
            self.view.set_status(f"Erro no preview: {error_msg}")
        if self._preview_dirty:
            self._preview_dirty = False
            self._run_preview()

    def on_export_file(self):
        if self.original_pil is None:
            QMessageBox.warning(self.view, "Aviso", "Nenhuma imagem carregada para exportar.")
            return

        # Nome padrão sugerido: <nome_base>_laser.bmp
        base_name = "gravacao_laser.bmp"
        if hasattr(self, "current_filename") and self.current_filename:
            name_no_ext = os.path.splitext(self.current_filename)[0]
            base_name = f"{name_no_ext}_laser.bmp"

        suggested_dir = os.path.dirname(self.current_filepath) if hasattr(self, "current_filepath") and self.current_filepath else os.path.expanduser("~")
        default_path = os.path.join(suggested_dir, base_name)

        save_path, selected_filter = QFileDialog.getSaveFileName(
            self.view,
            "Exportar Imagem para Gravação",
            default_path,
            "BMP (*.bmp);;PNG (*.png);;JPEG (*.jpg *.jpeg);;TIFF (*.tiff *.tif)"
        )
        if not save_path:
            return

        # Anexa extensão automaticamente caso omitida pelo usuário
        root, ext = os.path.splitext(save_path)
        if not ext:
            if "png" in selected_filter.lower():
                save_path += ".png"
            elif "jpg" in selected_filter.lower() or "jpeg" in selected_filter.lower():
                save_path += ".jpg"
            elif "tiff" in selected_filter.lower() or "tif" in selected_filter.lower():
                save_path += ".tiff"
            else:
                save_path += ".bmp"

        settings = self.view.sidebar.get_all_settings()
        settings["current_dpi"] = self.original_dpi
        current_key = self._make_preview_key(settings)
        cached_pil = self._last_dither_pil if (
            self._last_dither_pil is not None and self._last_preview_key == current_key
        ) else None

        self.view.sidebar.set_exporting_state(True)
        self.view.set_status(
            "Exportando imagem (100% idêntica ao preview)..."
            if cached_pil is not None
            else "Exportando imagem em resolução máxima..."
        )

        worker = ExportWorker(self.original_pil, settings, save_path, cached_pil=cached_pil)
        worker.signals.finished.connect(self._on_export_success)
        worker.signals.error.connect(self._on_export_error)
        self.thread_pool.start(worker)

    def _on_export_success(self, filepath):
        self.view.sidebar.set_exporting_state(False)
        self.view.set_status(f"Exportado com sucesso: {filepath}")
        QMessageBox.information(
            self.view,
            "Exportação Concluída",
            f"Imagem processada com sucesso e salva em:\n\n{filepath}"
        )

    def _on_export_error(self, error_msg):
        self.view.sidebar.set_exporting_state(False)
        self.view.set_status("Erro na exportação")
        QMessageBox.critical(self.view, "Erro na Exportação", error_msg)

    # --- Gerenciamento de Presets ---
    def on_preset_selected(self, name):
        preset = self.presets_mgr.get_preset(name)
        self.view.sidebar.apply_preset_settings(preset)
        self.view.set_status(f"Preset carregado: '{name}'")

    def on_preset_save(self):
        name, ok = QInputDialog.getText(
            self.view,
            "Salvar Predefinição",
            "Informe o nome para este preset:"
        )
        if ok and name.strip():
            settings = self.view.sidebar.get_all_settings()
            self.presets_mgr.save_preset(name.strip(), settings)
            presets = self.presets_mgr.list_presets()
            self.view.sidebar.update_presets_list(presets, current=name.strip())
            self.view.set_status(f"Preset '{name.strip()}' salvo com sucesso!")

    def on_preset_delete(self):
        current = self.view.sidebar.combo_presets.currentText()
        if self.presets_mgr.is_factory_preset(current):
            QMessageBox.information(
                self.view,
                "Aviso",
                f"O preset de fábrica '{current}' não pode ser excluído."
            )
            return

        reply = QMessageBox.question(
            self.view,
            "Confirmar Exclusão",
            f"Deseja realmente excluir a predefinição '{current}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.presets_mgr.delete_preset(current)
            presets = self.presets_mgr.list_presets()
            self.view.sidebar.update_presets_list(presets, current=DEFAULT_STARTUP_PRESET)
            self.view.sidebar.apply_preset_settings(self.presets_mgr.get_preset(DEFAULT_STARTUP_PRESET))
            self.view.set_status(f"Preset '{current}' excluído.")
