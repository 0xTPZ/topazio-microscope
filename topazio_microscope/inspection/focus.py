from collections import deque
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QWidget

class FocusPlot(QWidget):
    def __init__(self): super().__init__(); self.values=deque(maxlen=120); self.best=0; self.trend='—'; self.setMinimumHeight(100)
    def add_value(self, value):
        old=self.values[-1] if self.values else value; self.trend='aumentando' if value>old+1 else 'diminuindo' if value<old-1 else 'estável'; self.best=max(self.best,value); self.values.append(value); self.update()
    def reset(self): self.values.clear(); self.best=0; self.trend='—'; self.update()
    def paintEvent(self, event):
        painter=QPainter(self); painter.fillRect(self.rect(),QColor('#0d1622')); painter.setPen(QPen(QColor('#24405c'))); painter.drawRect(self.rect().adjusted(0,0,-1,-1))
        if len(self.values)<2: return
        pen=QPen(QColor('#d9aa3a')); pen.setWidth(2); painter.setPen(pen); vals=list(self.values); w=max(1,self.width()-12); h=max(1,self.height()-12)
        points=[QPointF(6+i*w/(len(vals)-1), 6+h-(v/100)*h) for i,v in enumerate(vals)]
        for a,b in zip(points,points[1:]): painter.drawLine(a,b)
