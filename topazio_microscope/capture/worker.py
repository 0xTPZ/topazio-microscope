import time
from PySide6.QtCore import QObject, Signal, Slot
import cv2

from .camera import BACKENDS

class CameraWorker(QObject):
    frame_ready = Signal(object)
    metadata = Signal(int, int, float)
    error = Signal(str)
    finished = Signal()

    def __init__(self, index: int, backend: str, width: int, height: int):
        super().__init__(); self.index = index; self.backend = backend; self.width = width; self.height = height; self.running = False; self.cap = None

    @Slot()
    def run(self):
        try:
            self.cap = cv2.VideoCapture(self.index, BACKENDS[self.backend])
            if not self.cap.isOpened(): self.error.emit(f'Não foi possível abrir a câmera {self.index} com {self.backend}'); return
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width); self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height); self.running = True; frame_count = 0; started = time.monotonic()
            while self.running:
                ok, frame = self.cap.read()
                if not ok or frame is None:
                    self.error.emit('A câmera não entregou um frame'); break
                h, w = frame.shape[:2]; frame_count += 1; elapsed = time.monotonic() - started; fps = frame_count / elapsed if elapsed > 0 else 0.0; self.metadata.emit(w, h, fps); self.frame_ready.emit(frame)
        except Exception as exc:
            self.error.emit(f'Erro na câmera: {exc}')
        finally:
            self.running = False
            if self.cap: self.cap.release(); self.cap = None
            self.finished.emit()

    @Slot()
    def stop(self):
        self.running = False
