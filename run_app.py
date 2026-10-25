from topazio_microscope.app_v02 import MainWindowV02
import sys
from PySide6.QtWidgets import QApplication

if __name__ == '__main__':
    application = QApplication(sys.argv)
    window = MainWindowV02()
    window.show()
    sys.exit(application.exec())
