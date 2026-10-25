import os
import sys
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).parents[1]))
from PySide6.QtWidgets import QApplication
from topazio_microscope.app_v02 import MainWindowV02

app = QApplication(sys.argv)
window = MainWindowV02()
for width, height in ((1024,600),(1280,720),(1366,768),(1920,1080),(2560,1440)):
    window.resize(width, height); window.show(); app.processEvents()
    assert window.video.width() > 150 and window.video.height() > 100
    assert window.scroll if hasattr(window, 'scroll') else True
    assert window.splitter.sizes()[0] > 0 and window.splitter.sizes()[1] > 0
    print(f'layout_{width}x{height}=OK video={window.video.width()}x{window.video.height()}')
window.close()
