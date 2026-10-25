"""Manual smoke test: requires the USB microscope connected."""
import os, sys
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0, str(Path(__file__).parents[1]))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from topazio_microscope.app_v02 import MainWindowV02

app=QApplication(sys.argv); win=MainWindowV02(); win.start_camera(); phases=[]
def start_original(): win.record_filtered.setChecked(False); win.toggle_record(); QTimer.singleShot(1200, stop_original)
def stop_original(): win.toggle_record(); win.zoom_slider.setValue(200); win.record_filtered.setChecked(True); QTimer.singleShot(300, start_processed)
def start_processed(): win.toggle_record(); QTimer.singleShot(1200, stop_processed)
def stop_processed():
    win.toggle_record(); phases.extend(str(p) for p in win.session.glob('*.avi')); print('recordings=', phases); win.close(); app.quit()
QTimer.singleShot(1500, start_original); app.exec()
