import os
import sys
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).parents[1]))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from topazio_microscope.app import MainWindow
app = QApplication(sys.argv)
window = MainWindow()
window.start()

def finish():
    print('camera_opened=', bool(window.cap and window.cap.isOpened()))
    print('frame_received=', window.last is not None)
    print('focus_value=', window.focus_bar.value())
    window.stop(); window.close(); app.quit()

QTimer.singleShot(2500, finish)
app.exec()
