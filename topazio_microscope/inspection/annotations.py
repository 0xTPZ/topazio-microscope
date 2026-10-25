import json
from dataclasses import dataclass, asdict
from pathlib import Path
from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QColor, QPen, QBrush, QPainterPath, QPixmap, QImage
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsPathItem, QGraphicsSimpleTextItem

@dataclass
class Annotation:
    kind: str; points: list; color: str = '#38bdf8'; width: int = 2; text: str = ''; layer: str = 'Inspeção'

class AnnotationModel:
    def __init__(self): self.items: list[Annotation] = []; self.redo_items: list[Annotation] = []
    def add(self, item): self.items.append(item); self.redo_items.clear()
    def undo(self):
        if self.items: self.redo_items.append(self.items.pop())
    def redo(self):
        if self.redo_items: self.items.append(self.redo_items.pop())
    def save(self, path: Path): path.write_text(json.dumps([asdict(i) for i in self.items], ensure_ascii=False, indent=2), encoding='utf-8')
    def load(self, path: Path): self.items = [Annotation(**x) for x in json.loads(path.read_text(encoding='utf-8'))]; self.redo_items.clear()

class AnnotationCanvas(QGraphicsView):
    changed = Signal()
    point_marked = Signal(float, float)
    def __init__(self):
        super().__init__(); self.scene = QGraphicsScene(self); self.setScene(self.scene); self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse); self.setDragMode(QGraphicsView.NoDrag); self.setBackgroundBrush(QColor('#0d1622')); self.model = AnnotationModel(); self.tool='select'; self.color='#38bdf8'; self.width=2; self.active_layer='Inspeção'; self.text_value='Texto'; self.drawing=False; self.start_point=QPointF(); self.temp=None; self.image_item=None; self.panning=False; self.last_pos=None
    def set_image(self, image: QImage):
        pix=QPixmap.fromImage(image); rect=self.scene.sceneRect(); old_center=self.mapToScene(self.viewport().rect().center()); self.scene.removeItem(self.image_item) if self.image_item else None; self.image_item=QGraphicsPixmapItem(pix); self.image_item.setZValue(-100); self.scene.addItem(self.image_item); self.scene.setSceneRect(pix.rect()); self.centerOn(old_center if rect.isValid() else QPointF(pix.width()/2,pix.height()/2)); self.rebuild()
    def set_tool(self, tool): self.tool=tool
    def wheelEvent(self, event): self.scale(1.15 if event.angleDelta().y()>0 else 1/1.15, 1.15 if event.angleDelta().y()>0 else 1/1.15)
    def mousePressEvent(self, event):
        p=self.mapToScene(event.position().toPoint())
        if event.button()==Qt.MiddleButton or (event.button()==Qt.LeftButton and self.tool=='pan'): self.panning=True; self.last_pos=event.position(); return
        if event.button()!=Qt.LeftButton or self.image_item is None: return
        self.start_point=p; self.stroke_points=[[p.x(),p.y()]]; self.drawing=True
        if self.tool=='point': self.point_marked.emit(p.x(),p.y()); self.drawing=False
    def mouseMoveEvent(self, event):
        if self.panning and self.last_pos is not None:
            delta=event.position()-self.last_pos; self.last_pos=event.position(); self.horizontalScrollBar().setValue(self.horizontalScrollBar().value()-int(delta.x())); self.verticalScrollBar().setValue(self.verticalScrollBar().value()-int(delta.y())); return
        if not self.drawing: return
        p=self.mapToScene(event.position().toPoint())
        if self.tool=='freehand': self.stroke_points.append([p.x(),p.y()]); return
        self.preview(self.start_point,p)
    def mouseReleaseEvent(self, event):
        if event.button()==Qt.MiddleButton or self.panning: self.panning=False; self.last_pos=None; return
        if not self.drawing: return
        p=self.mapToScene(event.position().toPoint()); self.drawing=False; self.commit(self.start_point,p)
    def preview(self,a,b):
        if self.temp: self.scene.removeItem(self.temp)
        pen=QPen(QColor(self.color)); pen.setWidth(self.width)
        if self.tool in ('line','arrow'): self.temp=self.scene.addLine(a.x(),a.y(),b.x(),b.y(),pen)
        elif self.tool=='circle': self.temp=self.scene.addEllipse(min(a.x(),b.x()),min(a.y(),b.y()),abs(b.x()-a.x()),abs(b.y()-a.y()),pen)
        elif self.tool=='rectangle': self.temp=self.scene.addRect(min(a.x(),b.x()),min(a.y(),b.y()),abs(b.x()-a.x()),abs(b.y()-a.y()),pen)
    def commit(self,a,b):
        if self.tool=='freehand': kind='freehand'; points=self.stroke_points if len(self.stroke_points)>1 else [[a.x(),a.y()],[b.x(),b.y()]]
        elif self.tool in ('line','arrow','circle','rectangle'): kind=self.tool; points=[[a.x(),a.y()],[b.x(),b.y()]]
        elif self.tool=='text': kind='text'; points=[[a.x(),a.y()]]
        else: return
        self.model.add(Annotation(kind,points,self.color,self.width,self.text_value if kind=='text' else '',self.active_layer)); self.rebuild(); self.changed.emit()
    def rebuild(self):
        for item in list(self.scene.items()):
            if item is not self.image_item: self.scene.removeItem(item)
        for ann in self.model.items:
            pen=QPen(QColor(ann.color)); pen.setWidth(ann.width); p1=QPointF(*ann.points[0]); p2=QPointF(*ann.points[-1])
            if ann.kind in ('line','arrow'): self.scene.addLine(p1.x(),p1.y(),p2.x(),p2.y(),pen)
            elif ann.kind=='circle': self.scene.addEllipse(min(p1.x(),p2.x()),min(p1.y(),p2.y()),abs(p2.x()-p1.x()),abs(p2.y()-p1.y()),pen)
            elif ann.kind=='rectangle': self.scene.addRect(min(p1.x(),p2.x()),min(p1.y(),p2.y()),abs(p2.x()-p1.x()),abs(p2.y()-p1.y()),pen)
            elif ann.kind=='text': t=self.scene.addSimpleText(ann.text or 'Texto'); t.setBrush(QBrush(QColor(ann.color))); t.setPos(p1)
            elif ann.kind=='freehand':
                path=QPainterPath(p1); [path.lineTo(QPointF(*point)) for point in ann.points[1:]]; self.scene.addPath(path,pen)
    def export_image(self, path: Path):
        image=QImage(self.scene.sceneRect().size().toSize(),QImage.Format_ARGB32); image.fill(QColor('#0d1622')); from PySide6.QtGui import QPainter; painter=QPainter(image); self.scene.render(painter); painter.end(); image.save(str(path))
