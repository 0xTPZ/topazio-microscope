import sys, time
from pathlib import Path
import cv2
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QSlider, QGroupBox, QProgressBar
from .capture.camera import BACKENDS
from .image.processing import apply_profile, focus_score

ROOT = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parents[1]
RESOURCE_ROOT = Path(getattr(sys, '_MEIPASS', ROOT))
ICON = RESOURCE_ROOT / 'assets' / 'topazio-microscope.ico'

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('Topázio Microscope — Inspeção eletrônica'); self.setWindowIcon(QIcon(str(ICON))); self.resize(1360, 860)
        self.cap = None; self.frozen = False; self.zoom = 1.0; self.last = None; self.writer = None
        self.video = QLabel('Selecione uma câmera e clique em Iniciar'); self.video.setAlignment(Qt.AlignCenter); self.video.setMinimumSize(640, 480); self.video.setStyleSheet('background:#10151d;color:#d9aa3a;font-size:18px')
        self.camera = QComboBox(); self.camera.addItems([str(i) for i in range(8)])
        self.backend = QComboBox(); self.backend.addItems(BACKENDS.keys())
        self.res = QComboBox(); self.res.addItems(['640x480','800x600','1280x720','1920x1080']); self.res.setCurrentText('1280x720')
        self.zoom_slider = QSlider(Qt.Horizontal); self.zoom_slider.setRange(100, 400); self.zoom_slider.setValue(100); self.zoom_slider.valueChanged.connect(lambda v: setattr(self, 'zoom', v/100))
        self.sharp_slider = QSlider(Qt.Horizontal); self.sharp_slider.setRange(0, 100); self.sharp_slider.setValue(25)
        self.profile = QComboBox(); self.profile.addItems(['Normal','Alto contraste','Realce de trilhas','Realce de solda','Escala de cinza','Detecção de bordas'])
        self.brightness = self.slider(-100, 100, 0); self.contrast = self.slider(50, 200, 100); self.saturation = self.slider(0, 200, 100); self.gamma = self.slider(50, 200, 100)
        self.focus_bar = QProgressBar(); self.focus_bar.setRange(0, 100); self.focus_bar.setValue(0); self.focus_bar.setFormat('Foco: %p%'); self.focus_label = QLabel('Foco não avaliado')
        self.status = QLabel('Pronto');
        controls = QVBoxLayout();
        controls.addWidget(self.group('Dispositivo', [('Câmera', self.camera), ('Backend', self.backend), ('Resolução', self.res)]))
        controls.addWidget(self.group('Imagem', [('Perfil', self.profile), ('Zoom digital', self.zoom_slider), ('Nitidez', self.sharp_slider), ('Brilho', self.brightness), ('Contraste', self.contrast), ('Saturação', self.saturation), ('Gama', self.gamma)]))
        controls.addWidget(QLabel('Qualidade de foco')); controls.addWidget(self.focus_bar); controls.addWidget(self.focus_label)
        for text, fn in [('Iniciar',self.start),('Parar',self.stop),('Congelar',self.freeze),('Fotografar',self.photo),('Gravar vídeo',self.record),('Tela cheia',self.fullscreen)]:
            b=QPushButton(text); b.clicked.connect(fn); controls.addWidget(b)
        controls.addStretch(); controls.addWidget(self.status)
        root=QHBoxLayout(); root.setContentsMargins(18,18,18,18); root.setSpacing(16); root.addWidget(self.video,1); panel=QWidget(); panel.setLayout(controls); panel.setFixedWidth(300); root.addWidget(panel)
        central=QWidget(); central.setLayout(root); self.setCentralWidget(central); self.timer=QTimer(self); self.timer.timeout.connect(self.update_frame); self.setStyleSheet('''QMainWindow{background:#080d14;color:#e8edf5} QWidget{color:#d7e1ee} QLabel#video{background:#0d1622;border:1px solid #24405c;border-radius:12px;color:#d9aa3a;font-size:18px} QGroupBox{color:#48b8ff;border:1px solid #21344a;border-radius:8px;margin-top:8px;padding-top:10px} QPushButton{background:#16283a;border:1px solid #2c5d82;border-radius:6px;padding:8px;color:#f2f6fb} QPushButton:hover{background:#1d405c;border-color:#d9aa3a} QComboBox{background:#0d1622;border:1px solid #2c5d82;padding:6px;color:#f2f6fb} QProgressBar{border:1px solid #2c5d82;border-radius:4px;text-align:center;background:#0d1622} QProgressBar::chunk{background:#d9aa3a;border-radius:3px}''')
    @staticmethod
    def slider(low, high, value):
        s=QSlider(Qt.Horizontal); s.setRange(low, high); s.setValue(value); return s
    @staticmethod
    def group(title, fields):
        box=QGroupBox(title); layout=QVBoxLayout(box); layout.setContentsMargins(8,14,8,8)
        for label, widget in fields: layout.addWidget(QLabel(label)); layout.addWidget(widget)
        return box
    def start(self):
        self.stop(); w,h=map(int,self.res.currentText().split('x')); self.cap=cv2.VideoCapture(int(self.camera.currentText()), BACKENDS[self.backend.currentText()]); self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,w); self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,h)
        if not self.cap.isOpened(): self.status.setText('Falha ao abrir câmera'); return
        self.timer.start(30); self.status.setText('Capturando')
    def stop(self):
        self.timer.stop();
        if self.cap: self.cap.release(); self.cap=None
        if self.writer: self.writer.release(); self.writer=None
    def update_frame(self):
        if self.frozen or not self.cap: return
        ok, frame=self.cap.read()
        if not ok: self.status.setText('Sem frame'); return
        self.last=frame; score=focus_score(frame); self.focus_bar.setValue(score.normalized); self.focus_label.setText('Imagem desfocada — ajuste a lente' if score.normalized < 25 else 'Foco aceitável'); self.render(frame)
        if self.writer: self.writer.write(frame)
    def render(self, frame):
        h,w=frame.shape[:2]; z=self.zoom; crop=frame[int(h*(1-1/z)/2):int(h*(1+1/z)/2),int(w*(1-1/z)/2):int(w*(1+1/z)/2)] if z>1 else frame
        processed=apply_profile(crop,self.profile.currentText(),self.brightness.value(),self.contrast.value()/100,self.saturation.value()/100,self.gamma.value()/100,self.sharp_slider.value()/100)
        rgb=cv2.cvtColor(processed,cv2.COLOR_BGR2RGB); q=QImage(rgb.data,rgb.shape[1],rgb.shape[0],rgb.strides[0],QImage.Format_RGB888); self.video.setPixmap(QPixmap.fromImage(q).scaled(self.video.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))
    def freeze(self): self.frozen=not self.frozen; self.status.setText('Congelado' if self.frozen else 'Capturando')
    def photo(self):
        if self.last is None: return
        out=ROOT/'captures'/f'photo_{time.strftime("%Y%m%d_%H%M%S")}.png'; out.parent.mkdir(exist_ok=True); cv2.imwrite(str(out),self.last); self.status.setText(f'Salvo: {out.name}')
    def record(self):
        if self.writer: self.writer.release(); self.writer=None; self.status.setText('Gravação parada'); return
        if self.last is None: return
        out=ROOT/'captures'/f'video_{time.strftime("%Y%m%d_%H%M%S")}.avi'; h,w=self.last.shape[:2]; self.writer=cv2.VideoWriter(str(out),cv2.VideoWriter_fourcc(*'MJPG'),20,(w,h)); self.status.setText('Gravando')
    def fullscreen(self): self.showFullScreen() if not self.isFullScreen() else self.showNormal()

if __name__ == '__main__': app=QApplication(sys.argv); win=MainWindow(); win.show(); sys.exit(app.exec())
