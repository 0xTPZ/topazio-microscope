import sys, time, math
from collections import deque
from pathlib import Path
import cv2
from PySide6.QtCore import Qt, QThread, QTimer, Signal, QSettings
from PySide6.QtGui import QImage, QPixmap, QIcon, QColor
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton, QComboBox, QSlider, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QProgressBar, QTabWidget, QListWidget, QListWidgetItem, QFileDialog, QCheckBox, QLineEdit, QMessageBox, QColorDialog, QSpinBox, QSplitter, QScrollArea, QSizePolicy, QPlainTextEdit, QFrame)
from .capture.camera import BACKENDS
from .capture.worker import CameraWorker
from .capture.recording import VideoRecorder
from .image.processing import apply_profile, focus_score
from .inspection.annotations import Annotation, AnnotationModel, AnnotationCanvas
from .inspection.focus import FocusPlot
from .analysis.assistant import analyze_frame
from .models.repair import RepairReport, TestResult
from .reports.repair import export_markdown, export_visual_result
from .rules.repair import build_repair_guidance
from .storage.paths import capture_root, session_root
from .ui.controls import slider_row
from .ui.roi_canvas import RoiCanvas
from .vision.alignment import compare_images, overlay_images
from .vision.metrics import sharpness_score
from .ui.theme import TOPAZIO_QSS

RESOURCE_ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).parents[1]))
ICON = RESOURCE_ROOT / 'assets' / 'topazio-microscope.ico'

class MainWindowV02(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('Topázio Microscope v0.2 — Inspeção eletrônica'); self.setWindowIcon(QIcon(str(ICON))); self.resize(1440, 900)
        self.thread=None; self.worker=None; self.last=None; self.processed=None; self.writer=None; self.record_size=None; self.display_loaded=False; self.session=session_root(); self.zoom=1.0; self.frozen=False; self.plan_points=[]; self.before_path=None; self.after_path=None
        self.assistant_frame=None; self.assistant_compare_frame=None; self.assistant_result=None; self.assistant_comparison=None; self.assistant_source=''; self.assistant_live=False; self.assistant_roi=None; self.assistant_focus_values=deque(maxlen=120); self.assistant_focus_best=-1; self.assistant_best_frame=None; self.assistant_live_tick=0; self.assistant_history_data=[]
        self.tabs=QTabWidget(); self.setCentralWidget(self.tabs); self.build_capture_tab(); self.build_inspection_tab(); self.build_planning_tab(); self.build_focus_tab(); self.build_assistant_tab(); self.apply_style()

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
        box=QWidget(); lay=QVBoxLayout(box); lay.setContentsMargins(12,12,12,12); lay.addWidget(QLabel('Ferramentas disponíveis nas abas Inspeção, Planejamento, Foco assistido e Assistente.')); lay.addWidget(self.focus_bar); lay.addWidget(self.focus_label); lay.addWidget(self.button('Abrir Inspeção',lambda:self.tabs.setCurrentIndex(1))); lay.addWidget(self.button('Abrir Planejamento',lambda:self.tabs.setCurrentIndex(2))); lay.addWidget(self.button('Abrir Foco assistido',lambda:self.tabs.setCurrentIndex(3))); lay.addWidget(self.button('Abrir Assistente',lambda:self.tabs.setCurrentIndex(4))); lay.addStretch(); return box
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
    def build_assistant_tab(self):
        self.assistant_canvas=RoiCanvas(); self.assistant_canvas.roi_selected.connect(self.assistant_roi_selected)
        self.assistant_canvas.setToolTip('Arraste sobre a imagem para selecionar a região de interesse (ROI)')
        self.assistant_source_label=QLabel('Fonte: nenhuma — use o último frame ou importe uma imagem')
        self.assistant_roi_label=QLabel('ROI: quadro completo até que uma região seja selecionada')
        self.assistant_status=QLabel('A análise é local, offline e auxiliar; não confirma continuidade elétrica.')
        self.assistant_focus_bar=QProgressBar(); self.assistant_focus_bar.setRange(0,100); self.assistant_focus_bar.setFormat('Nitidez ROI: %p%')
        self.assistant_focus_label=QLabel('Foco assistido: selecione uma ROI')
        self.assistant_focus_plot=FocusPlot(); self.assistant_focus_plot.setMinimumHeight(80)
        self.assistant_roi_preview=QLabel('Miniatura da ROI'); self.assistant_roi_preview.setAlignment(Qt.AlignCenter); self.assistant_roi_preview.setMinimumHeight(90); self.assistant_roi_preview.setStyleSheet('border: 1px solid #24405c;')
        self.assistant_observations=QListWidget(); self.assistant_hypotheses=QListWidget(); self.assistant_verifications=QListWidget(); self.assistant_test_results=QListWidget(); self.assistant_history=QListWidget()
        result_tabs=QTabWidget(); result_tabs.addTab(self.assistant_observations,'Observações'); result_tabs.addTab(self.assistant_hypotheses,'Hipóteses'); result_tabs.addTab(self.assistant_verifications,'Verificações'); result_tabs.addTab(self.assistant_test_results,'Resultados'); result_tabs.addTab(self.assistant_history,'Histórico')
        self.assistant_test_name=QLineEdit(); self.assistant_test_name.setPlaceholderText('Teste / medição')
        self.assistant_test_value=QLineEdit(); self.assistant_test_value.setPlaceholderText('Resultado')
        self.assistant_test_note=QLineEdit(); self.assistant_test_note.setPlaceholderText('Observação opcional')
        test_form=QGridLayout(); test_form.addWidget(self.assistant_test_name,0,0); test_form.addWidget(self.assistant_test_value,0,1); test_form.addWidget(self.assistant_test_note,1,0,1,2); test_form.addWidget(self.button('Registrar resultado',self.assistant_add_test_result),2,0,1,2)
        self.assistant_notes=QPlainTextEdit(); self.assistant_notes.setPlaceholderText('Planejamento e notas do técnico. Caminhos são hipóteses visuais; valide com esquema e multímetro.')
        self.assistant_align=QCheckBox('Alinhar comparação com ORB/RANSAC'); self.assistant_overlay=QSlider(Qt.Horizontal); self.assistant_overlay.setRange(0,100); self.assistant_overlay.setValue(50); self.assistant_overlay.valueChanged.connect(self.assistant_refresh_overlay)
        self.assistant_panel=QFrame(); self.assistant_panel.setObjectName('assistantPanel'); panel_lay=QVBoxLayout(self.assistant_panel); panel_lay.setContentsMargins(10,10,10,10)
        buttons=QGridLayout(); buttons.addWidget(self.button('Acompanhar câmera',self.assistant_follow_camera),0,0); buttons.addWidget(self.button('Usar último frame',self.assistant_use_last),0,1); buttons.addWidget(self.button('Importar imagem',self.assistant_import_image),1,0); buttons.addWidget(self.button('Analisar',self.assistant_analyze),1,1); buttons.addWidget(self.button('Capturar melhor frame',self.assistant_capture_best),2,0); buttons.addWidget(self.button('Importar comparação',self.assistant_import_comparison),2,1); buttons.addWidget(self.button('Mostrar overlay',self.assistant_show_overlay),3,0); buttons.addWidget(self.button('Mostrar análise',self.assistant_show_analysis),3,1); buttons.addWidget(self.button('Exportar imagem',self.assistant_export_image),4,0); buttons.addWidget(self.button('Exportar relatório',self.assistant_export_report),4,1)
        panel_lay.addLayout(buttons); panel_lay.addWidget(self.assistant_source_label); panel_lay.addWidget(self.assistant_roi_label); panel_lay.addWidget(self.assistant_roi_preview); panel_lay.addWidget(self.assistant_focus_bar); panel_lay.addWidget(self.assistant_focus_label); panel_lay.addWidget(self.assistant_focus_plot); panel_lay.addWidget(QLabel('Transparência da sobreposição')); panel_lay.addWidget(self.assistant_overlay); panel_lay.addWidget(self.assistant_align); panel_lay.addWidget(result_tabs,1); panel_lay.addWidget(QLabel('Registrar medição ou observação')); panel_lay.addLayout(test_form); panel_lay.addWidget(QLabel('Planejamento')); panel_lay.addWidget(self.assistant_notes); panel_lay.addWidget(self.assistant_status)
        self.assistant_panel.setMinimumWidth(300)
        self.assistant_panel_scroll=QScrollArea(); self.assistant_panel_scroll.setWidgetResizable(True); self.assistant_panel_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.assistant_panel_scroll.setWidget(self.assistant_panel)
        self.assistant_toggle=self.button('Recolher painel',self.toggle_assistant_panel)
        preview=QWidget(); preview_lay=QVBoxLayout(preview); preview_lay.setContentsMargins(8,8,8,8); preview_lay.addWidget(self.assistant_toggle,0,Qt.AlignRight); preview_lay.addWidget(self.assistant_canvas,1)
        splitter=QSplitter(Qt.Horizontal); splitter.addWidget(preview); splitter.addWidget(self.assistant_panel_scroll); splitter.setCollapsible(0,False); splitter.setCollapsible(1,True); splitter.setStretchFactor(0,1); splitter.setSizes([820,420]); self.assistant_splitter=splitter
        lay=QVBoxLayout(); lay.setContentsMargins(0,0,0,0); lay.addWidget(splitter); tab=QWidget(); tab.setLayout(lay); self.tabs.addTab(tab,'Assistente')

    def toggle_assistant_panel(self):
        visible=self.assistant_panel_scroll.isVisible(); self.assistant_panel_scroll.setVisible(not visible); self.assistant_toggle.setText('Mostrar painel' if visible else 'Recolher painel')

    def assistant_reset_analysis(self):
        self.assistant_result=None; self.assistant_comparison=None; self.assistant_compare_frame=None; self.assistant_focus_values.clear(); self.assistant_focus_best=-1; self.assistant_best_frame=None; self.assistant_focus_plot.reset(); self.assistant_focus_bar.setValue(0); self.assistant_focus_label.setText('Foco assistido: selecione uma ROI'); self.assistant_observations.clear(); self.assistant_hypotheses.clear(); self.assistant_verifications.clear(); self.assistant_test_results.clear(); self.assistant_roi_preview.setText('Miniatura da ROI'); self.assistant_report=RepairReport(source=self.assistant_source)

    def assistant_set_source(self, frame, label, live=False):
        self.assistant_frame=frame.copy(); self.assistant_source=label; self.assistant_live=live; self.assistant_roi=None; self.assistant_canvas.clear_selection(); self.assistant_canvas.set_frame(self.assistant_frame); self.assistant_source_label.setText(f'Fonte: {label}'); self.assistant_roi_label.setText('ROI: quadro completo até que uma região seja selecionada'); self.assistant_reset_analysis(); self.assistant_status.setText('Imagem pronta para análise visual local.')

    def assistant_follow_camera(self):
        if self.last is None: self.assistant_status.setText('Inicie a câmera para acompanhar frames'); return
        self.assistant_live=True; self.assistant_frame=self.last.copy(); self.assistant_source='captura USB ao vivo'; self.assistant_source_label.setText('Fonte: captura USB ao vivo'); self.assistant_canvas.set_frame(self.assistant_frame); self.assistant_status.setText('Acompanhando a câmera; selecione uma ROI para acompanhar a nitidez.')

    def assistant_use_last(self):
        if self.last is None: self.assistant_status.setText('Nenhum frame disponível'); return
        self.assistant_set_source(self.last,'último frame capturado')

    def assistant_import_image(self):
        path,_=QFileDialog.getOpenFileName(self,'Importar imagem para o Assistente',str(capture_root()),'Imagens (*.png *.jpg *.jpeg)')
        if not path: return
        frame=cv2.imread(path)
        if frame is None: self.assistant_status.setText('Não foi possível abrir a imagem'); return
        self.assistant_set_source(frame,Path(path).name)

    def assistant_roi_selected(self,x,y,width,height):
        self.assistant_roi=(x,y,width,height); self.assistant_roi_label.setText(f'ROI: x={x}, y={y}, largura={width}, altura={height} px'); self.assistant_update_roi_preview(); self.assistant_focus_values.clear(); self.assistant_focus_best=-1; self.assistant_best_frame=None; self.assistant_focus_plot.reset(); self.assistant_measure_focus(self.assistant_frame)

    def assistant_update_roi_preview(self):
        if self.assistant_frame is None or not self.assistant_roi: return
        x,y,width,height=self.assistant_roi; crop=self.assistant_frame[y:y+height,x:x+width]
        if crop.size: self.assistant_roi_preview.setPixmap(QPixmap.fromImage(self.to_qimage(crop)).scaled(260,130,Qt.KeepAspectRatio,Qt.SmoothTransformation))

    def assistant_measure_focus(self,frame):
        if frame is None or not self.assistant_roi: return
        x,y,width,height=self.assistant_roi; crop=frame[y:y+height,x:x+width]
        if crop.size == 0: return
        value=focus_score(crop).normalized; previous=self.assistant_focus_values[-1] if self.assistant_focus_values else value; self.assistant_focus_values.append(value); self.assistant_focus_plot.add_value(value); self.assistant_focus_bar.setValue(value); trend='melhorando' if value>previous+1 else 'piorando' if value<previous-1 else 'estável'; self.assistant_focus_label.setText(f'Foco ROI: {value}% · {trend} · melhor {max(self.assistant_focus_values)}%')
        if value>self.assistant_focus_best: self.assistant_focus_best=value; self.assistant_best_frame=frame.copy()

    def assistant_update_live(self,frame):
        if not self.assistant_live: return
        self.assistant_frame=frame.copy(); self.assistant_live_tick+=1
        if self.assistant_live_tick%4==0: self.assistant_canvas.set_frame(self.assistant_frame); self.assistant_update_roi_preview()
        self.assistant_measure_focus(frame)

    def assistant_analyze(self):
        if self.assistant_frame is None: self.assistant_status.setText('Carregue um frame ou imagem antes de analisar'); return
        try: result=analyze_frame(self.assistant_frame,self.assistant_roi)
        except ValueError as exc: self.assistant_status.setText(str(exc)); return
        guidance=build_repair_guidance(result); self.assistant_result=result; self.assistant_report=RepairReport(source=self.assistant_source,roi=result.roi.to_dict() if result.roi else None,observations=guidance['observations'],hypotheses=guidance['hypotheses'],verifications=guidance['verifications'],analysis=result.to_dict(),methods=result.methods,warnings=guidance['warnings'],planning_notes=self.assistant_notes.toPlainText())
        self.assistant_observations.addItems(guidance['observations']); self.assistant_hypotheses.addItems([f"{item['text']} · incerteza: {item['uncertainty']} · base: {item['basis']}" for item in guidance['hypotheses']]); self.assistant_verifications.addItems(guidance['verifications']); self.assistant_canvas.set_frame(result.highlighted); self.assistant_history_data.append(self.assistant_report.to_dict()); self.assistant_history.addItem(f"{time.strftime('%H:%M:%S')} · {self.assistant_source or 'imagem'} · {len(result.suspicion_regions)} região(ões)"); self.assistant_status.setText('Análise concluída por OpenCV/NumPy e regras explícitas; hipótese visual, não confirmação elétrica.')

    def assistant_import_comparison(self):
        path,_=QFileDialog.getOpenFileName(self,'Importar imagem para comparação',str(capture_root()),'Imagens (*.png *.jpg *.jpeg)')
        if not path: return
        frame=cv2.imread(path)
        if frame is None: self.assistant_status.setText('Não foi possível abrir a comparação'); return
        self.assistant_compare_frame=frame; self.assistant_status.setText(f'Comparação carregada: {Path(path).name}. Clique em Mostrar overlay.')

    def assistant_show_overlay(self):
        if self.assistant_frame is None or self.assistant_compare_frame is None: self.assistant_status.setText('Carregue uma imagem de comparação primeiro'); return
        self.assistant_comparison=compare_images(self.assistant_frame,self.assistant_compare_frame,self.assistant_overlay.value()/100.0,self.assistant_align.isChecked()); self.assistant_report.comparison=self.assistant_comparison.to_dict(); self.assistant_canvas.set_frame(self.assistant_comparison.overlay); self.assistant_status.setText(f"Overlay pronto · diferença média {self.assistant_comparison.mean_difference:.1f} · pixels alterados {self.assistant_comparison.changed_ratio*100:.1f}%")

    def assistant_refresh_overlay(self):
        if self.assistant_comparison is None: return
        self.assistant_comparison.overlay=overlay_images(self.assistant_frame,self.assistant_comparison.aligned,self.assistant_overlay.value()/100.0); self.assistant_canvas.set_frame(self.assistant_comparison.overlay)

    def assistant_show_analysis(self):
        if self.assistant_result is not None: self.assistant_canvas.set_frame(self.assistant_result.highlighted); self.assistant_status.setText('Visualização da análise: regiões candidatas destacadas em amarelo.')
        elif self.assistant_frame is not None: self.assistant_canvas.set_frame(self.assistant_frame)

    def assistant_capture_best(self):
        if self.assistant_best_frame is None: self.assistant_status.setText('Ainda não há melhor frame; acompanhe a câmera com uma ROI selecionada'); return
        self.last=self.assistant_best_frame.copy(); self.display_loaded=False; self.render(self.last); self.save_capture(); self.assistant_status.setText('Melhor frame da ROI capturado e salvo na galeria.')

    def assistant_add_test_result(self):
        name=self.assistant_test_name.text().strip(); value=self.assistant_test_value.text().strip(); note=self.assistant_test_note.text().strip()
        if not name or not value: self.assistant_status.setText('Informe o nome do teste e o resultado'); return
        item=TestResult(name,value,note); self.assistant_report.test_results.append(item); self.assistant_test_results.addItem(f'{name}: {value}' + (f' — {note}' if note else '')); self.assistant_test_name.clear(); self.assistant_test_value.clear(); self.assistant_test_note.clear(); self.assistant_status.setText('Resultado manual registrado no relatório.')

    def assistant_export_image(self):
        if self.assistant_frame is None: self.assistant_status.setText('Nenhuma imagem carregada'); return
        path,_=QFileDialog.getSaveFileName(self,'Exportar resultado visual',str(self.session/'repair_assistant.png'),'PNG (*.png)')
        if not path: return
        image=self.assistant_result.highlighted if self.assistant_result is not None else self.assistant_frame; self.assistant_status.setText('Imagem exportada.' if export_visual_result(image,Path(path)) else 'Falha ao exportar imagem.')

    def assistant_export_report(self):
        self.assistant_report.planning_notes=self.assistant_notes.toPlainText(); path,_=QFileDialog.getSaveFileName(self,'Exportar relatório do Assistente',str(self.session/'repair_report.json'),'JSON (*.json);;Markdown (*.md)')
        if not path: return
        if Path(path).suffix.lower()=='.md': export_markdown(self.assistant_report,Path(path))
        else: self.assistant_report.save(Path(path))
        self.assistant_status.setText(f'Relatório exportado: {Path(path).name}')
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
        self.last=frame.copy(); self.display_loaded=False; score=focus_score(frame); self.focus_bar.setValue(score.normalized); self.focus_plot.add_value(score.normalized); self.focus_label.setText(f'Foco {self.focus_plot.trend} · melhor {self.focus_plot.best}%'); self.render(frame); self.assistant_update_live(frame)
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
