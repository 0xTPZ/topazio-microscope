import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from topazio_microscope.capture.worker import CameraWorker
from topazio_microscope.capture.recording import normalize_frame

class FakeCapture:
    def __init__(self, *_args): self.opened=True; self.released=False; self.count=0
    def isOpened(self): return self.opened
    def set(self, *_args): return True
    def read(self):
        self.count += 1
        return True, np.zeros((480, 640, 3), dtype=np.uint8)
    def get(self, *_args): return 0
    def release(self): self.released=True

def test_worker_lifecycle_without_camera():
    fake = FakeCapture()
    with patch('topazio_microscope.capture.worker.cv2.VideoCapture', return_value=fake):
        worker = CameraWorker(0, 'DirectShow', 1280, 720); frames=[]; worker.frame_ready.connect(lambda frame: (frames.append(frame), worker.stop()))
        worker.run()
    assert frames and fake.released

def test_recording_dimensions_with_zoom():
    source = np.zeros((240, 320, 3), dtype=np.uint8)
    normalized = normalize_frame(source, (640, 480))
    assert normalized.shape == (480, 640, 3)

def test_video_recorder_keeps_dimensions():
    class FakeWriter:
        def __init__(self): self.frames=[]; self.released=False
        def isOpened(self): return True
        def write(self, frame): self.frames.append(frame.shape)
        def release(self): self.released=True
    fake=FakeWriter()
    with patch('topazio_microscope.capture.recording.cv2.VideoWriter', return_value=fake):
        from topazio_microscope.capture.recording import VideoRecorder
        recorder=VideoRecorder(Path(tempfile.gettempdir())/'topazio_test.avi',(640,480)); recorder.write(np.zeros((240,320,3),dtype=np.uint8)); recorder.write(np.zeros((480,640,3),dtype=np.uint8)); recorder.release()
    assert fake.frames == [(480,640,3),(480,640,3)] and fake.released
