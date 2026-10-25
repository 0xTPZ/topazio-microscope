from pathlib import Path
import cv2
import numpy as np

def normalize_frame(frame: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    width, height = size
    if frame is None or frame.size == 0:
        raise ValueError('frame vazio')
    if frame.shape[1] == width and frame.shape[0] == height:
        return frame
    return cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

class VideoRecorder:
    def __init__(self, path: Path, size: tuple[int, int], fps: float = 20.0):
        self.path = Path(path); self.size = size; self.writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'MJPG'), fps, size)
        if not self.writer.isOpened():
            self.writer.release(); raise RuntimeError(f'Não foi possível abrir o gravador: {path}')
    def write(self, frame): self.writer.write(normalize_frame(frame, self.size))
    def release(self):
        if self.writer: self.writer.release(); self.writer = None
