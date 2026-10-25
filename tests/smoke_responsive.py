import os
import sys
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).parents[1]))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from topazio_microscope.app_v02 import MainWindowV02

app = QApplication(sys.argv)
window = MainWindowV02()
assert window.splitter.count() == 2
assert window.tool_tabs.count() == 4
assert window.tabs.count() == 5
assert not window.plan_canvas.has_image()
window.plan_canvas.set_image(QImage(320, 240, QImage.Format_RGB32))
assert window.plan_canvas.has_image()
assert window.assistant_canvas.frame is None
window.start_camera()

def finish():
    print('responsive_splitter=OK')
    print('camera_opened=', bool(window.worker))
    print('frame_received=', window.last is not None)
    print('actual_resolution=', window.actual.text())
    window.close(); app.quit()

QTimer.singleShot(3000, finish)
app.exec()
