import numpy as np
from topazio_microscope.image.processing import apply_profile, focus_score

def test_focus_and_profiles():
    frame = np.zeros((80, 120, 3), dtype=np.uint8)
    frame[:, 55:65] = 255
    score = focus_score(frame)
    assert score.normalized >= 0
    for profile in ('Normal', 'Alto contraste', 'Realce de trilhas', 'Realce de solda', 'Escala de cinza', 'Detecção de bordas'):
        result = apply_profile(frame, profile)
        assert result.shape == frame.shape
