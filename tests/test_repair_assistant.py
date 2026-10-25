import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).parents[1]))

import cv2
import numpy as np
from PySide6.QtWidgets import QApplication

from topazio_microscope.analysis.assistant import analyze_frame
from topazio_microscope.analysis.providers import OptionalONNXProvider
from topazio_microscope.models.repair import RepairReport, TestResult
from topazio_microscope.rules.repair import build_repair_guidance
from topazio_microscope.vision.alignment import compare_images
from topazio_microscope.vision.metrics import ROI, crop_roi, sharpness_score


def sample_frame():
    frame = np.zeros((360, 520, 3), dtype=np.uint8)
    cv2.rectangle(frame, (40, 40), (470, 300), (80, 120, 160), 3)
    cv2.line(frame, (50, 180), (470, 180), (220, 220, 220), 5)
    cv2.line(frame, (180, 55), (180, 290), (180, 220, 100), 4)
    cv2.putText(frame, 'TPZ', (250, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3)
    return frame


def test_roi_metrics_and_explicit_guidance():
    frame = sample_frame()
    crop, roi = crop_roi(frame, (40, 40, 220, 180))
    assert roi == ROI(40, 40, 220, 180)
    assert crop.shape[:2] == (180, 220)
    assert sharpness_score(frame, roi) > 0
    result = analyze_frame(frame, roi)
    guidance = build_repair_guidance(result)
    assert result.highlighted.shape == frame.shape
    assert 'OpenCV' in result.methods
    assert guidance['observations'] and guidance['verifications']
    assert any('não confirma' in warning.lower() for warning in guidance['warnings'])


def test_comparison_overlay_and_difference():
    base = sample_frame()
    changed = base.copy()
    cv2.line(changed, (300, 180), (420, 180), (0, 0, 0), 12)
    comparison = compare_images(base, changed, alpha=0.35, align=False)
    assert comparison.overlay.shape == base.shape
    assert comparison.difference.shape == base.shape[:2]
    assert comparison.changed_ratio > 0
    assert comparison.alignment.success is False


def test_report_roundtrip_and_manual_result():
    report = RepairReport(source='fixture.png', roi=ROI(2, 3, 40, 50).to_dict())
    report.observations.append('Borda visual candidata')
    report.test_results.append(TestResult('Continuidade', '0.2 ohm', 'medição manual'))
    path = Path(tempfile.gettempdir()) / 'topazio_repair_assistant_report.json'
    report.save(path)
    loaded = RepairReport.load(path)
    assert loaded.source == 'fixture.png'
    assert loaded.roi == {'x': 2, 'y': 3, 'width': 40, 'height': 50}
    assert loaded.test_results[0].value == '0.2 ohm'


def test_optional_model_provider_is_offline_and_explicit():
    provider = OptionalONNXProvider()
    result = provider.analyze(sample_frame())
    assert result['available'] is False
    assert 'Nenhum modelo ONNX' in result['message']


def test_assistant_interface_initialization_and_analysis():
    app = QApplication.instance() or QApplication([])
    from topazio_microscope.app_v02 import MainWindowV02
    window = MainWindowV02()
    assert window.tabs.count() == 5
    frame = sample_frame()
    window.assistant_set_source(frame, 'fixture.png')
    window.assistant_roi_selected(40, 40, 220, 180)
    window.assistant_analyze()
    assert window.assistant_canvas.frame is not None
    assert window.assistant_observations.count() > 0
    assert window.assistant_hypotheses.count() > 0
    window.close()
    app.processEvents()


def test_orb_alignment_with_sparse_descriptors():
    """Imagens sem pontos suficientes devem retornar falha explicativa, não exceção."""
    from topazio_microscope.vision.alignment import align_images_orb
    blank = np.zeros((120, 160, 3), dtype=np.uint8)
    outcome = align_images_orb(blank, blank)
    assert not outcome.success


def test_assistant_report_initialized_and_results_replaced():
    app = QApplication.instance() or QApplication([])
    from topazio_microscope.app_v02 import MainWindowV02
    window = MainWindowV02()
    assert window.assistant_report is not None
    frame = sample_frame()
    window.assistant_set_source(frame, 'fixture.png')
    window.assistant_analyze()
    count = window.assistant_observations.count()
    assert count > 0
    window.assistant_analyze()
    assert window.assistant_observations.count() == count
    window.close()
    app.processEvents()


def test_roi_canvas_repeated_frames_with_selection():
    """Ao reconstruir a cena, nenhuma referência a item já destruído deve sobreviver."""
    app = QApplication.instance() or QApplication([])
    from topazio_microscope.ui.roi_canvas import RoiCanvas
    view = RoiCanvas()
    view.set_frame(sample_frame())
    view.roi = (20, 20, 60, 60)
    view._draw_selection()
    view.set_frame(sample_frame())
    view.clear_selection()
    assert view.selection_item is None
    view.close()
    app.processEvents()
