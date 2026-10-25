from dataclasses import dataclass
from pathlib import Path
import time
import cv2

@dataclass
class CameraResult:
    index: int
    backend: str
    opened: bool
    frames: int = 0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    fourcc: str = ''
    error: str = ''

BACKENDS = {'DirectShow': cv2.CAP_DSHOW, 'Media Foundation': cv2.CAP_MSMF}

def probe(index: int, backend_name: str, fourcc: str | None = None, width=1280, height=720) -> CameraResult:
    api = BACKENDS[backend_name]
    cap = cv2.VideoCapture(index, api)
    result = CameraResult(index, backend_name, cap.isOpened())
    if not result.opened:
        result.error = 'VideoCapture não abriu o dispositivo'
        return result
    if fourcc:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    start = time.monotonic()
    for _ in range(8):
        ok, frame = cap.read()
        if ok and frame is not None and frame.size:
            result.frames += 1
            result.width, result.height = frame.shape[1], frame.shape[0]
    elapsed = max(time.monotonic() - start, 1e-6)
    result.fps = result.frames / elapsed
    actual = int(cap.get(cv2.CAP_PROP_FOURCC))
    result.fourcc = ''.join(chr((actual >> 8*i) & 0xff) for i in range(4)).strip() or 'unknown'
    cap.release()
    if not result.frames:
        result.error = 'abriu, mas não entregou frames'
    return result

def scan(max_index=8):
    results = []
    for index in range(max_index):
        for backend in BACKENDS:
            for fmt in (None, 'MJPG', 'YUY2'):
                results.append(probe(index, backend, fmt))
    return results

def capture_sample(index, backend_name, output: Path):
    cap = cv2.VideoCapture(index, BACKENDS[backend_name])
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        raise RuntimeError('Não foi possível capturar um frame')
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), frame)
    return frame.shape[1], frame.shape[0]
