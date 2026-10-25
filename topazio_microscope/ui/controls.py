from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QLabel, QSlider, QVBoxLayout, QHBoxLayout, QSizePolicy

def slider_row(label: str, slider: QSlider, minimum: int, maximum: int, tooltip: str, scale: float = 1.0):
    container = QWidget(); container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    title = QLabel(label); value = QLabel(); value.setAlignment(Qt.AlignRight | Qt.AlignVCenter); value.setMinimumWidth(42)
    slider.setRange(minimum, maximum); slider.setToolTip(tooltip); title.setToolTip(tooltip)
    def update(v): value.setText(f'{v / scale:.0f}' if scale != 1 else str(v))
    slider.valueChanged.connect(update); update(slider.value())
    header = QHBoxLayout(); header.setContentsMargins(0, 0, 0, 0); header.addWidget(title); header.addWidget(value)
    layout = QVBoxLayout(container); layout.setContentsMargins(0, 2, 0, 4); layout.setSpacing(1); layout.addLayout(header); layout.addWidget(slider)
    return container
