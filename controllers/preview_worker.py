from PySide6.QtCore import QRunnable, QObject, Signal
import engine


class WorkerSignals(QObject):
    finished = Signal(int, object) # generation_id, QImage
    error = Signal(int, str)       # generation_id, error_message


class PreviewWorker(QRunnable):
    def __init__(self, preview_img, settings, generation: int):
        super().__init__()
        self.preview_img = preview_img
        self.settings = settings
        self.generation = generation
        self.signals = WorkerSignals()

    def run(self):
        try:
            result_pil = engine.process_live_preview(self.preview_img, self.settings, preview_mode=True)
            qimg = engine.pil_to_qimage(result_pil)
            self.signals.finished.emit(self.generation, qimg)
        except Exception as e:
            self.signals.error.emit(self.generation, str(e))


class ExportSignals(QObject):
    finished = Signal(str)
    error = Signal(str)


class ExportWorker(QRunnable):
    def __init__(self, original_pil, settings, save_path: str):
        super().__init__()
        self.original_pil = original_pil
        self.settings = settings
        self.save_path = save_path
        self.signals = ExportSignals()

    def run(self):
        try:
            result_pil = engine.process_live_preview(self.original_pil, self.settings, preview_mode=False)
            result_pil.save(self.save_path)
            self.signals.finished.emit(self.save_path)
        except Exception as e:
            self.signals.error.emit(str(e))
