from dataclasses import asdict, dataclass
from typing import Iterable

import cv2
import numpy as np


@dataclass(frozen=True)
class ROI:
    """Região em coordenadas da imagem original, nunca em coordenadas da tela."""

    x: int
    y: int
    width: int
    height: int

    def clipped(self, shape: Iterable[int]) -> 'ROI':
        height, width = int(shape[0]), int(shape[1])
        x = max(0, min(self.x, max(0, width - 1)))
        y = max(0, min(self.y, max(0, height - 1)))
        right = max(x + 1, min(width, self.x + self.width))
        bottom = max(y + 1, min(height, self.y + self.height))
        return ROI(x, y, max(1, right - x), max(1, bottom - y))

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_roi(roi, shape) -> ROI | None:
    if roi is None:
        return None
    if isinstance(roi, ROI):
        return roi.clipped(shape)
    if isinstance(roi, dict):
        return ROI(int(roi['x']), int(roi['y']), int(roi['width']), int(roi['height'])).clipped(shape)
    values = list(roi)
    if len(values) != 4:
        raise ValueError('ROI deve conter x, y, largura e altura')
    return ROI(*(int(value) for value in values)).clipped(shape)


def crop_roi(frame: np.ndarray, roi=None) -> tuple[np.ndarray, ROI | None]:
    normalized = normalize_roi(roi, frame.shape[:2])
    if normalized is None:
        return frame, None
    return frame[normalized.y:normalized.y + normalized.height,
                 normalized.x:normalized.x + normalized.width], normalized


def _gray(frame: np.ndarray) -> np.ndarray:
    if frame.ndim == 2:
        return frame
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


def sharpness_score(frame: np.ndarray, roi=None) -> float:
    crop, _ = crop_roi(frame, roi)
    gray = _gray(crop)
    if gray.size == 0:
        return 0.0
    laplacian = cv2.Laplacian(gray, cv2.CV_64F).var()
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    tenengrad = float(np.mean(sobel_x * sobel_x + sobel_y * sobel_y))
    return float(laplacian * 0.55 + tenengrad * 0.0045)


def enhance_edges(frame: np.ndarray, roi=None) -> np.ndarray:
    crop, normalized = crop_roi(frame, roi)
    gray = _gray(crop)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    median = float(np.median(enhanced))
    low = int(max(20, 0.66 * median))
    high = int(min(255, max(low + 20, 1.33 * median)))
    edges = cv2.Canny(enhanced, low, high)
    result = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    if normalized is None:
        return result
    canvas = frame.copy()
    canvas[normalized.y:normalized.y + normalized.height,
           normalized.x:normalized.x + normalized.width] = result
    return canvas


@dataclass(frozen=True)
class SuspicionRegion:
    x: int
    y: int
    width: int
    height: int
    score: float
    reason: str = 'descontinuidade geométrica visual candidata'

    def to_dict(self) -> dict:
        return {
            'x': self.x, 'y': self.y, 'width': self.width, 'height': self.height,
            'score': round(float(self.score), 4), 'reason': self.reason,
        }


def detect_visual_suspicions(frame: np.ndarray, roi=None) -> list[SuspicionRegion]:
    """Encontra gaps geométricos em bordas; não interpreta continuidade elétrica."""
    crop, normalized = crop_roi(frame, roi)
    gray = _gray(crop)
    if gray.size == 0:
        return []
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blur, 50, 150)
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    gaps = cv2.subtract(closed, edges)
    gaps = cv2.morphologyEx(gaps, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(gaps, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = max(4.0, gray.shape[0] * gray.shape[1] * 0.00002)
    ox = normalized.x if normalized else 0
    oy = normalized.y if normalized else 0
    result = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue
        x, y, width, height = cv2.boundingRect(contour)
        score = min(1.0, area / max(1.0, width * height))
        result.append(SuspicionRegion(x + ox, y + oy, width, height, score))
    return sorted(result, key=lambda item: item.score, reverse=True)[:20]


def highlight_suspicions(frame: np.ndarray, regions: list[SuspicionRegion]) -> np.ndarray:
    result = frame.copy()
    for region in regions:
        cv2.rectangle(result, (region.x, region.y),
                      (region.x + region.width, region.y + region.height), (0, 190, 255), 2)
        cv2.putText(result, 'visual?', (region.x, max(16, region.y - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 190, 255), 1, cv2.LINE_AA)
    return result
