import os
from PIL import Image
from PySide6.QtCore import QObject, QTimer, QThreadPool
from PySide6.QtWidgets import QFileDialog, QMessageBox, QInputDialog

from views.main_window import MainWindow
from core.presets_manager import PresetsManager
from controllers.preview_worker import PreviewWorker, ExportWorker
import engine

PREVIEW_MAX_PX = 1600


class AppController(QObject):
    def __init__(self, main_window: MainWindow):
        super().__init__()
        self.view = main_window
        self.presets_mgr = PresetsManager()

        self.original_pil = None
        self.original_dpi = (72, 72)
        self.current_filepath = None
        self.current_filename = None
        self.preview_generation = 0

        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._run_preview)

        self.thread_pool = QThreadPool.globalInstance()

        self._connect_signals()
        self._init_presets()

    def _connect_signals(self):
        sb = self.view.sidebar
        sb.openFileClicked.connect(self.on_open_file)
        sb.exportClicked.connect(self.on_export_file)
        sb.settingsChanged.connect(self.on_settings_changed)
        sb.presetSelected.connect(self.on_preset_selected)
        sb.presetSaveClicked.connect(self.on_preset_save)
        sb.presetDeleteClicked.connect(self.on_preset_delete)

    def _init_presets(self):
        presets = self.presets_mgr.list_presets()
        self.view.sidebar.update_presets_list(presets, current="Padrão")

    def _downscale_for_preview(self, pil_img, target_w=0, target_h=0):
        # Se dimensões de corte foram calculadas, utiliza a escala real do laser com teto de performance
        if target_w > 0 and target_h > 0:
            cur_w, cur_h = target_w, target_h
            if max(cur_w, cur_h) > PREVIEW_MAX_PX:
                scale = PREVIEW_MAX_PX / max(cur_w, cur_h)
                cur_w = max(1, int(cur_w * scale))
                cur_h = max(1, int(cur_h * scale))
            if pil_img.size != (cur_w, cur_h):
                return pil_img.resize((cur_w, cur_h), Image.LANCZOS)
            return pil_img

        w, h = pil_img.size
        if max(w, h) <= PREVIEW_MAX_PX:
            return pil_img
        ratio = PREVIEW_MAX_PX / max(w, h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        return pil_img.resize((new_w, new_h), Image.LANCZOS)

    def on_open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self.view,
            "Selecionar Imagem",
            "",
            "Imagens (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.gif *.webp);;Todos os arquivos (*.*)"
        )
        if not filepath:
            return

        try:
            pil_img, dpi = engine.load_image_pillow(filepath)
            self.original_pil = pil_img
            self.original_dpi = dpi
            self.current_filepath = filepath
            self.current_filename = os.path.basename(filepath)

            w, h = pil_img.size
            mp = (w * h) / 1_000_000
            dpi_val = dpi[0] if isinstance(dpi, tuple) else dpi

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

            # Normalização de tamanho para o visualizador (mesma resolução base do preview)
            preview_orig = self._downscale_for_preview(pil_img)
            qimg = engine.pil_to_qimage(preview_orig)
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
        width_mm = settings["width_mm"]
        height_mm = settings["height_mm"]
        target_dpi = settings["target_dpi"]

        out_w = round(width_mm / 25.4 * target_dpi)
        out_h = round(height_mm / 25.4 * target_dpi)
        total_mp = (out_w * out_h) / 1_000_000

        out1 = f"Saída: {out_w}x{out_h} px | {total_mp:.2f} MP"

        if total_mp > 10:
            alert = "⚠ Resolução muito alta!"
            alert_color = "#ef4444"
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

        self.preview_generation += 1
        gen = self.preview_generation

        # Feedback visual imediato: ativa spinner animado e atualiza status
        self.view.viewer.set_loading(True, "Processando simulação...")
        self.view.sidebar.lbl_res_alert.setText("Processando simulação...")

        settings = self.view.sidebar.get_all_settings()
        settings["current_dpi"] = self.original_dpi

        width_mm = settings.get("width_mm", 0)
        height_mm = settings.get("height_mm", 0)
        target_dpi = settings.get("target_dpi", 300)
        target_w = round(width_mm / 25.4 * target_dpi) if width_mm > 0 else 0
        target_h = round(height_mm / 25.4 * target_dpi) if height_mm > 0 else 0

        # Prepara a imagem de preview na resolução real de saída do laser (com teto de performance)
        preview_img = self._downscale_for_preview(self.original_pil, target_w=target_w, target_h=target_h)

        worker = PreviewWorker(preview_img, settings, gen)
        worker.signals.finished.connect(self._on_preview_finished)
        worker.signals.error.connect(self._on_preview_error)

        self.thread_pool.start(worker)

    def _on_preview_finished(self, generation, qimg):
        if generation == self.preview_generation:
            self.view.viewer.set_simulated_image(qimg, "Simulação atualizada")
            # Sincroniza a dimensão da cena do canvas original para zoom/pan 1:1 perfeito
            if self.view.viewer.canvas_orig.pixmap_item.pixmap().size() != qimg.size():
                orig_resized = self.original_pil.resize((qimg.width(), qimg.height()), Image.LANCZOS)
                self.view.viewer.canvas_orig.set_image(engine.pil_to_qimage(orig_resized))
            self._update_resolution_info()

    def _on_preview_error(self, generation, error_msg):
        if generation == self.preview_generation:
            self.view.viewer.set_loading(False, "Erro no processamento")
            self.view.set_status(f"Erro no preview: {error_msg}")

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

        self.view.sidebar.set_exporting_state(True)
        self.view.set_status("Exportando imagem em resolução máxima...")

        worker = ExportWorker(self.original_pil, settings, save_path)
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
        if current == "Padrão":
            QMessageBox.information(
                self.view,
                "Aviso",
                "O preset de fábrica 'Padrão' não pode ser excluído."
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
            self.view.sidebar.update_presets_list(presets, current="Padrão")
            self.view.set_status(f"Preset '{current}' excluído.")
