import sys, time, math
from pathlib import Path
import cv2
from PySide6.QtCore import Qt, QThread, QTimer, Signal, QSettings
from PySide6.QtGui import QImage, QPixmap, QIcon, QColor
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton, QComboBox, QSlider, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QProgressBar, QTabWidget, QListWidget, QListWidgetItem, QFileDialog, QCheckBox, QLineEdit, QMessageBox, QColorDialog, QSpinBox, QSplitter, QScrollArea, QSizePolicy)
from .capture.camera import BACKENDS
from .capture.worker import CameraWorker
from .capture.recording import VideoRecorder
from .image.processing import apply_profile, focus_score
from .inspection.annotations import Annotation, AnnotationModel, AnnotationCanvas
from .inspection.focus import FocusPlot
from .storage.paths import capture_root, session_root
from .ui.controls import slider_row
from .ui.theme import TOPAZIO_QSS

RESOURCE_ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).parents[1]))
ICON = RESOURCE_ROOT / 'assets' / 'topazio-microscope.ico'

class MainWindowV02(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('Topázio Microscope v0.2 — Inspeção eletrônica'); self.setWindowIcon(QIcon(str(ICON))); self.resize(1440, 900)
        self.thread=None; self.worker=None; self.last=None; self.processed=None; self.writer=None; self.record_size=None; self.display_loaded=False; self.session=session_root(); self.zoom=1.0; self.frozen=False; self.plan_points=[]; self.before_path=None; self.after_path=None
        self.tabs=QTabWidget(); self.setCentralWidget(self.tabs); self.build_capture_tab(); self.build_inspection_tab(); self.build_planning_tab(); self.build_focus_tab(); self.apply_style()

    def slider(self, low, high, value):
        s=QSlider(Qt.Horizontal); s.setRange(low,high); s.setValue(value); return s
    def group(self, title, fields):
        box=QGroupBox(title); lay=QVBoxLayout(box); lay.setContentsMargins(8,14,8,8)
        for name, widget in fields: lay.addWidget(QLabel(name)); lay.addWidget(widget)
        return box
    def button(self, text, fn):
        b=QPushButton(text); b.clicked.connect(fn); return b
    def build_capture_tab(self):
        self.video=QLabel('Selecione a câmera e clique em Iniciar'); self.video.setAlignment(Qt.AlignCenter); self.video.setMinimumSize(180,120); self.video.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding); self.video.setObjectName('video')
        self.camera=QComboBox(); self.camera.addItems([str(i) for i in range(8)]); self.camera.setToolTip('Índice do dispositivo de câmera exposto pelo OpenCV')
        self.backend=QComboBox(); self.backend.addItems(BACKENDS.keys()); self.backend.setToolTip('Backend de captura do Windows')
        self.res=QComboBox(); self.res.addItems(['640x480','800x600','1280x720','1920x1080']); self.res.setCurrentText('1280x720')
        self.profile=QComboBox(); self.profile.addItems(['Normal','Alto contraste','Realce de trilhas','Realce de solda','Escala de cinza','Detecção de bordas'])
        self.zoom_slider=self.slider(100,400,100); self.zoom_slider.valueChanged.connect(lambda v: setattr(self,'zoom',v/100))
        self.sharp=self.slider(0,100,25); self.brightness=self.slider(-100,100,0); self.contrast=self.slider(50,200,100); self.saturation=self.slider(0,200,100); self.gamma=self.slider(50,200,100)
        self.record_filtered=QCheckBox('Gravar vídeo processado'); self.focus_bar=QProgressBar(); self.focus_bar.setRange(0,100); self.focus_bar.setFormat('Foco: %p%'); self.focus_label=QLabel('Foco não avaliado'); self.actual=QLabel('Resolução real: —'); self.status=QLabel('Pronto')
        self.tool_tabs=QTabWidget(); self.tool_tabs.addTab(self.camera_controls(),'Câmera'); self.tool_tabs.addTab(self.image_controls(),'Imagem'); self.tool_tabs.addTab(self.inspection_controls(),'Inspeção'); self.tool_tabs.addTab(self.capture_controls(),'Captura')
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); scroll.setWidget(self.tool_tabs); scroll.setMinimumWidth(220); scroll.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Expanding); self.scroll=scroll
        self.gallery=QListWidget(); self.gallery.setViewMode(QListWidget.IconMode); self.gallery.setIconSize(self.gallery.iconSize()); self.gallery.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed); self.gallery.setMaximumHeight(112); self.gallery.itemDoubleClicked.connect(self.open_gallery_item)
        viewer=QWidget(); viewer_lay=QVBoxLayout(viewer); viewer_lay.setContentsMargins(12,12,8,8); viewer_lay.addWidget(self.video,1); viewer_lay.addWidget(QLabel('Galeria da sessão')); viewer_lay.addWidget(self.gallery)
        splitter=QSplitter(Qt.Horizontal); splitter.addWidget(viewer); splitter.addWidget(scroll); splitter.setCollapsible(0,False); splitter.setCollapsible(1,True); splitter.setStretchFactor(0,1); splitter.setStretchFactor(1,0); splitter.setSizes([900,340]); self.splitter=splitter
        settings=QSettings('TopazioLabs','TopazioMicroscope'); state=settings.value('captureSplitter')
        if state: splitter.restoreState(state)
        lay=QVBoxLayout(); lay.setContentsMargins(0,0,0,0); lay.addWidget(splitter); tab=QWidget(); tab.setLayout(lay); self.tabs.addTab(tab,'Captura')

    def camera_controls(self):
        box=QWidget(); lay=QVBoxLayout(box); lay.setContentsMargins(12,12,12,12); lay.addWidget(self.group('Dispositivo',[('Câmera',self.camera),('Backend',self.backend),('Resolução solicitada',self.res)])); lay.addWidget(self.actual); lay.addWidget(self.button('Iniciar captura',self.start_camera)); lay.addWidget(self.button('Parar captura',self.stop_camera)); lay.addStretch(); return box
    def image_controls(self):
        box=QWidget(); lay=QVBoxLayout(box); lay.setContentsMargins(12,12,12,12); lay.addWidget(QLabel('Ajustes de visualização'))
        for name,slider,lo,hi,tip,scale in [('Zoom',self.zoom_slider,100,400,'Ampliação digital; use a roda no painel de inspeção',100),('Nitidez',self.sharp,0,100,'Realce local, sem recuperar foco óptico',100),('Brilho',self.brightness,-100,100,'Offset de luminosidade',1),('Contraste',self.contrast,50,200,'Escala de contraste',100),('Saturação',self.saturation,0,200,'Intensidade das cores',100),('Gama',self.gamma,50,200,'Curva de luminância',100)]: lay.addWidget(slider_row(name,slider,lo,hi,tip,scale))
        lay.addWidget(QLabel('Perfil')); lay.addWidget(self.profile); lay.addWidget(self.button('Restaurar valores padrão',self.reset_image)); lay.addStretch(); return box
    def inspection_controls(self):
        box=QWidget(); lay=QVBoxLayout(box); lay.setContentsMargins(12,12,12,12); lay.addWidget(QLabel('Ferramentas disponíveis nas abas Inspeção, Planejamento e Foco assistido.')); lay.addWidget(self.focus_bar); lay.addWidget(self.focus_label); lay.addWidget(self.button('Abrir Inspeção',lambda:self.tabs.setCurrentIndex(1))); lay.addWidget(self.button('Abrir Planejamento',lambda:self.tabs.setCurrentIndex(2))); lay.addWidget(self.button('Abrir Foco assistido',lambda:self.tabs.setCurrentIndex(3))); lay.addStretch(); return box
    def capture_controls(self):
        box=QWidget(); lay=QVBoxLayout(box); lay.setContentsMargins(12,12,12,12); lay.addWidget(self.button('Salvar original + processada',self.save_capture)); lay.addWidget(self.button('Iniciar/parar gravação',self.toggle_record)); lay.addWidget(self.record_filtered); lay.addWidget(self.button('Congelar quadro',self.freeze)); lay.addWidget(self.button('Abrir pasta de capturas',self.open_capture_folder)); lay.addWidget(self.button('Tela cheia',self.fullscreen)); lay.addWidget(self.status); lay.addStretch(); return box
    def build_inspection_tab(self):
        self.inspect_canvas=AnnotationCanvas(); self.inspect_canvas.set_tool('select'); self.inspect_canvas.changed.connect(self.refresh_inspect)
        self.inspect_tool=QComboBox(); self.inspect_tool.addItems(['select','line','arrow','circle','rectangle','freehand','text','pan']); self.inspect_tool.currentTextChanged.connect(self.inspect_canvas.set_tool)
        self.inspect_layer=QComboBox(); self.inspect_layer.addItems(['Inspeção','Referência','Defeito','Reparo']); self.inspect_layer.currentTextChanged.connect(lambda v: setattr(self.inspect_canvas,'active_layer',v))
        self.inspect_color=QPushButton('Cor'); self.inspect_color.clicked.connect(self.choose_inspect_color); self.inspect_width=QSpinBox(); self.inspect_width.setRange(1,12); self.inspect_width.setValue(2); self.inspect_width.valueChanged.connect(lambda v: setattr(self.inspect_canvas,'width',v))
        self.inspect_text=QLineEdit('Texto'); self.inspect_canvas.text_value='Texto'; self.inspect_text.textChanged.connect(lambda v: setattr(self.inspect_canvas,'text_value',v))
        bar=QGridLayout(); bar.setHorizontalSpacing(8); bar.setVerticalSpacing(6); bar.addWidget(QLabel('Ferramenta'),0,0); bar.addWidget(self.inspect_tool,0,1); bar.addWidget(QLabel('Camada'),0,2); bar.addWidget(self.inspect_layer,0,3); bar.addWidget(QLabel('Cor/espessura'),1,0); bar.addWidget(self.inspect_color,1,1); bar.addWidget(self.inspect_width,1,2); bar.addWidget(self.inspect_text,1,3); bar.addWidget(self.button('Desfazer',self.inspect_undo),2,0); bar.addWidget(self.button('Refazer',self.inspect_redo),2,1); bar.addWidget(self.button('Salvar anotações',self.save_annotations),2,2); bar.addWidget(self.button('Carregar',self.load_annotations),2,3); bar.addWidget(self.button('Exportar imagem',self.export_inspection),3,0,1,4)
        lay=QVBoxLayout(); lay.addLayout(bar); lay.addWidget(self.inspect_canvas); tab=QWidget(); tab.setLayout(lay); self.tabs.addTab(tab,'Inspeção')
    def build_planning_tab(self):
        self.plan_canvas=AnnotationCanvas(); self.plan_canvas.point_marked.connect(self.plan_point)
        self.plan_notes=QLineEdit(); self.plan_notes.setPlaceholderText('Notas do planejamento — hipótese visual, validar com esquema/multímetro')
        self.plan_status=QLabel('Nenhum ponto marcado. Os caminhos não confirmam ligação elétrica.')
        self.plan_before=QLabel('Antes'); self.plan_after=QLabel('Depois'); self.plan_before.setAlignment(Qt.AlignCenter); self.plan_after.setAlignment(Qt.AlignCenter)
        self.plan_source=QLabel('Imagem: nenhuma'); controls=QGridLayout(); controls.setHorizontalSpacing(8); controls.setVerticalSpacing(6); controls.addWidget(self.button('Usar último frame',self.load_last_into_canvases),0,0); controls.addWidget(self.button('Importar imagem',self.import_planning_image),0,1); controls.addWidget(self.button('Marcar ponto',lambda:self.plan_canvas.set_tool('point')),0,2); controls.addWidget(self.button('Desenhar caminho',lambda:self.plan_canvas.set_tool('line')),1,0); controls.addWidget(self.button('Medir pixels',self.measure_plan),1,1); controls.addWidget(self.button('Exportar planejamento',self.export_plan),1,2); controls.addWidget(self.button('Escolher antes',lambda:self.choose_compare('before')),2,0); controls.addWidget(self.button('Escolher depois',lambda:self.choose_compare('after')),2,1); controls.addWidget(self.plan_source,3,0,1,3)
        compare=QHBoxLayout(); compare.addWidget(self.plan_before); compare.addWidget(self.plan_after); lay=QVBoxLayout(); lay.addLayout(controls); lay.addWidget(self.plan_canvas,1); lay.addWidget(self.plan_notes); lay.addWidget(self.plan_status); lay.addLayout(compare); tab=QWidget(); tab.setLayout(lay); self.tabs.addTab(tab,'Planejamento de Trilhas')
    def build_focus_tab(self):
        self.focus_plot=FocusPlot(); self.focus_info=QLabel('A métrica é local e auxiliar; não é autofoco físico.'); reset=self.button('Redefinir melhor resultado',self.focus_plot.reset); lay=QVBoxLayout(); lay.addWidget(QLabel('Foco assistido — região central do quadro')); lay.addWidget(self.focus_plot); lay.addWidget(self.focus_info); lay.addWidget(reset); tab=QWidget(); tab.setLayout(lay); self.tabs.addTab(tab,'Foco assistido')
    def apply_style(self):
        self.setStyleSheet(TOPAZIO_QSS)
    def reset_image(self):
        for widget, value in ((self.zoom_slider,100),(self.sharp,25),(self.brightness,0),(self.contrast,100),(self.saturation,100),(self.gamma,100)): widget.setValue(value)
        self.profile.setCurrentIndex(0)
    def start_camera(self):
        if self.worker:
            self.stop_camera()
            if self.thread:
                self.thread.quit()
                if not self.thread.wait(2000): self.status.setText('A câmera ainda está encerrando; tente novamente'); return
                self.thread.deleteLater()
            self.thread=None; self.worker=None
        w,h=map(int,self.res.currentText().split('x')); self.thread=QThread(); self.worker=CameraWorker(int(self.camera.currentText()),self.backend.currentText(),w,h); self.worker.moveToThread(self.thread); self.thread.started.connect(self.worker.run); self.worker.frame_ready.connect(self.on_frame); self.worker.metadata.connect(self.on_metadata); self.worker.error.connect(self.on_camera_error); self.worker.finished.connect(self.thread.quit); self.thread.finished.connect(self.camera_finished); self.thread.start(); self.status.setText('Capturando sem bloquear a interface')
    def stop_camera(self):
        if self.worker: self.worker.stop(); self.status.setText('Parando câmera…')
    def camera_finished(self):
        if self.thread and not self.thread.isRunning(): self.thread.deleteLater(); self.thread=None; self.worker=None
    def on_camera_error(self,msg): self.status.setText(msg)
    def on_metadata(self,w,h,fps): self.actual.setText(f'Resolução real: {w}×{h} · {fps:.1f} FPS')
    def on_frame(self,frame):
        if self.frozen: return
        self.last=frame.copy(); self.display_loaded=False; score=focus_score(frame); self.focus_bar.setValue(score.normalized); self.focus_plot.add_value(score.normalized); self.focus_label.setText(f'Foco {self.focus_plot.trend} · melhor {self.focus_plot.best}%'); self.render(frame)
        if self.writer: self.writer.write(self.processed if self.record_filtered.isChecked() else frame)
    def render(self,frame,reprocess=True):
        h,w=frame.shape[:2]; z=self.zoom; crop=frame[int(h*(1-1/z)/2):int(h*(1+1/z)/2),int(w*(1-1/z)/2):int(w*(1+1/z)/2)] if reprocess and z>1 else frame; self.processed=apply_profile(crop,self.profile.currentText(),self.brightness.value(),self.contrast.value()/100,self.saturation.value()/100,self.gamma.value()/100,self.sharp.value()/100) if reprocess else crop.copy(); rgb=cv2.cvtColor(self.processed,cv2.COLOR_BGR2RGB); q=QImage(rgb.data,rgb.shape[1],rgb.shape[0],rgb.strides[0],QImage.Format_RGB888); self.video.setPixmap(QPixmap.fromImage(q).scaled(self.video.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))
    def freeze(self): self.frozen=not self.frozen; self.status.setText('Quadro congelado' if self.frozen else 'Capturando')
    def save_capture(self):
        if self.last is None: self.status.setText('Nenhum frame disponível'); return
        stamp=time.strftime('%Y%m%d_%H%M%S'); raw=self.session/f'{stamp}_original.png'; processed=self.session/f'{stamp}_processada.png'; cv2.imwrite(str(raw),self.last); cv2.imwrite(str(processed),self.processed if self.processed is not None else self.last); self.add_gallery(processed); self.status.setText(f'Original e processada salvas em {self.session}')
    def toggle_record(self):
        if self.writer: self.writer.release(); self.writer=None; self.status.setText('Gravação parada'); return
        if self.last is None: return
        h,w=self.last.shape[:2]; out=self.session/f'video_{time.strftime("%Y%m%d_%H%M%S")}.avi'
        try: self.writer=VideoRecorder(out,(w,h),20); self.record_size=(w,h)
        except RuntimeError as exc: self.writer=None; self.status.setText(str(exc)); return
        self.status.setText('Gravando vídeo '+('processado' if self.record_filtered.isChecked() else 'original'))
    def add_gallery(self,path): item=QListWidgetItem(QIcon(str(path)),path.name); item.setData(Qt.UserRole,str(path)); self.gallery.addItem(item)
    def open_gallery_item(self,item):
        frame=cv2.imread(item.data(Qt.UserRole))
        if frame is None: self.status.setText('Não foi possível abrir a captura'); return
        self.last=frame; self.display_loaded=True; self.render(frame,reprocess=False); self.load_last_into_canvases(); self.tabs.setCurrentIndex(1)
    def open_capture_folder(self): import os; os.startfile(str(self.session))
    def to_qimage(self,frame): rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB); return QImage(rgb.data,rgb.shape[1],rgb.shape[0],rgb.strides[0],QImage.Format_RGB888).copy()
    def choose_inspect_color(self): color=QColorDialog.getColor(QColor(self.inspect_canvas.color),self); self.inspect_canvas.color=color.name() if color.isValid() else self.inspect_canvas.color
    def load_last_into_canvases(self):
        if self.last is not None:
            image=self.to_qimage(self.processed if self.processed is not None else self.last); self.inspect_canvas.set_image(image); self.set_planning_image(image,'último frame/captura processada')
    def load_last_into_canvas(self): self.load_last_into_canvases()
    def import_planning_image(self):
        path,_=QFileDialog.getOpenFileName(self,'Importar imagem para planejamento',str(capture_root()),'Imagens (*.png *.jpg *.jpeg)')
        if not path: return
        frame=cv2.imread(path)
        if frame is None: self.plan_status.setText('Não foi possível importar a imagem'); return
        self.last=frame; self.processed=frame.copy(); self.display_loaded=True; self.set_planning_image(self.to_qimage(frame),Path(path).name)
    def set_planning_image(self,image,label):
        self.plan_points.clear(); self.plan_canvas.model=AnnotationModel(); self.plan_canvas.set_image(image); self.plan_source.setText(f'Imagem: {label}')
    def inspect_undo(self): self.inspect_canvas.model.undo(); self.inspect_canvas.rebuild()
    def inspect_redo(self): self.inspect_canvas.model.redo(); self.inspect_canvas.rebuild()
    def save_annotations(self): path,_=QFileDialog.getSaveFileName(self,'Salvar anotações',str(self.session/'annotations.json'),'JSON (*.json)'); self.inspect_canvas.model.save(Path(path)) if path else None
    def load_annotations(self):
        path,_=QFileDialog.getOpenFileName(self,'Carregar anotações',str(capture_root()),'JSON (*.json)')
        if path: self.inspect_canvas.model.load(Path(path)); self.inspect_canvas.rebuild()
    def export_inspection(self): path,_=QFileDialog.getSaveFileName(self,'Exportar inspeção',str(self.session/'inspecao_anotada.png'),'PNG (*.png)'); self.inspect_canvas.export_image(Path(path)) if path else None
    def refresh_inspect(self): pass
    def plan_point(self,x,y):
        self.plan_points.append((x,y)); self.plan_status.setText(f'Ponto {len(self.plan_points)} marcado em ({x:.0f}, {y:.0f}) px'); self.plan_canvas.set_tool('select')
        if len(self.plan_points)>=2: a,b=self.plan_points[-2:]; self.plan_canvas.model.add(Annotation('line',[[a[0],a[1]],[b[0],b[1]]],'#d9aa3a',3,'','Planejamento')); self.plan_canvas.rebuild()
    def measure_plan(self):
        if len(self.plan_points)<2: self.plan_status.setText('Marque dois pontos primeiro'); return
        a,b=self.plan_points[-2:]; self.plan_status.setText(f'Comprimento visual: {math.dist(a,b):.1f} px — não é medida física')
    def export_plan(self): path,_=QFileDialog.getSaveFileName(self,'Exportar planejamento',str(self.session/'planejamento_trilhas.png'),'PNG (*.png)'); self.plan_canvas.export_image(Path(path)) if path else None
    def choose_compare(self,which):
        path,_=QFileDialog.getOpenFileName(self,'Selecionar imagem',str(capture_root()),'Imagens (*.png *.jpg *.jpeg)')
        if not path: return
        pix=QPixmap(path).scaled(420,220,Qt.KeepAspectRatio,Qt.SmoothTransformation); (self.plan_before if which=='before' else self.plan_after).setPixmap(pix); setattr(self,which+'_path',path)
    def fullscreen(self): self.showFullScreen() if not self.isFullScreen() else self.showNormal()
    def closeEvent(self,event):
        self.stop_camera()
        if self.thread:
            self.thread.quit()
            if not self.thread.wait(2000): event.ignore(); return
        self.writer.release() if self.writer else None
        if hasattr(self,'splitter'): QSettings('TopazioLabs','TopazioMicroscope').setValue('captureSplitter',self.splitter.saveState())
        event.accept()

if __name__ == '__main__':
    app=QApplication(sys.argv); win=MainWindowV02(); win.show(); sys.exit(app.exec())
