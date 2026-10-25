"""Smoke test manual: usa o microscópio USB, mas não exige câmera no CI."""
import os
import sys
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).parents[1]))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from topazio_microscope.app_v02 import MainWindowV02


app = QApplication(sys.argv)
window = MainWindowV02()
window.start_camera()


def finish():
    if window.last is not None:
        window.assistant_set_source(window.last, 'microscópio USB real')
        height, width = window.last.shape[:2]
        window.assistant_roi_selected(max(0, width // 8), max(0, height // 8), max(20, width // 2), max(20, height // 2))
        window.assistant_analyze()
        print('assistant_usb_frame=', window.last.shape[1], 'x', window.last.shape[0])
        print('assistant_usb_observations=', window.assistant_observations.count())
        print('assistant_usb_hypotheses=', window.assistant_hypotheses.count())
        print('assistant_usb_focus=', window.assistant_focus_bar.value())
    else:
        print('assistant_usb_frame=None')
    window.close()
    app.quit()


QTimer.singleShot(3500, finish)
app.exec()
