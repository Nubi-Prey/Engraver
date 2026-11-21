from PySide6.QtCore import QRunnable, QObject, Signal
import engine


class WorkerSignals(QObject):
    # generation_id, preview_key, PIL.Image (1-bit), QImage (1-bit), QImage (pre-dither)
    finished = Signal(int, object, object, object, object)
    error = Signal(int, str)  # generation_id, error_message


class PreviewWorker(QRunnable):
    """Executa exatamente o mesmo pipeline da exportação (preview_mode=False) para 100% de fidelidade."""

    def __init__(self, original_pil, settings, generation: int, preview_key=None):
        super().__init__()
        self.original_pil = original_pil
        self.settings = settings
        self.generation = generation
        self.preview_key = preview_key
        self.signals = WorkerSignals()

    def run(self):
        try:
            dither_pil, pre_dither_pil = engine.process_live_preview(
                self.original_pil,
                self.settings,
                preview_mode=False,
                return_pre_dither=True,
            )
            qimg_dither = engine.pil_to_qimage(dither_pil)
            qimg_pre = engine.pil_to_qimage(pre_dither_pil)
            self.signals.finished.emit(
                self.generation,
                self.preview_key,
                dither_pil,
                qimg_dither,
                qimg_pre,
            )
        except Exception as e:
            self.signals.error.emit(self.generation, str(e))


class ExportSignals(QObject):
    finished = Signal(str)
    error = Signal(str)


class ExportWorker(QRunnable):
    """Salva o resultado 1-bit reaproveitando o cache do preview quando idêntico, com DPI embutido."""

    def __init__(self, original_pil, settings, save_path: str, cached_pil=None):
        super().__init__()
        self.original_pil = original_pil
        self.settings = settings
        self.save_path = save_path
        self.cached_pil = cached_pil
        self.signals = ExportSignals()

    def run(self):
        try:
            if self.cached_pil is not None:
                result_pil = self.cached_pil
            else:
                result_pil = engine.process_live_preview(
                    self.original_pil,
                    self.settings,
                    preview_mode=False,
                )
            out_dpi = engine.resolve_output_dpi(self.settings)
            engine.save_engraving_image(result_pil, self.save_path, dpi=out_dpi)
            self.signals.finished.emit(self.save_path)
        except Exception as e:
            self.signals.error.emit(str(e))
