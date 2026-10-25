from dataclasses import dataclass
import cv2
import numpy as np

@dataclass(frozen=True)
class FocusScore:
    laplacian: float
    tenengrad: float

    @property
    def normalized(self) -> int:
        value = min(100.0, (self.laplacian / 180.0) * 55.0 + (self.tenengrad / 9000.0) * 45.0)
        return int(max(0.0, value))

def focus_score(frame: np.ndarray) -> FocusScore:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    lap = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    ten = float(np.mean(sobel_x * sobel_x + sobel_y * sobel_y))
    return FocusScore(lap, ten)

def apply_profile(frame: np.ndarray, profile: str, brightness=0, contrast=1.0,
                  saturation=1.0, gamma=1.0, sharpness=0.25) -> np.ndarray:
    out = frame.copy()
    if profile == 'Escala de cinza':
        gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY); out = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    elif profile == 'Alto contraste':
        contrast = max(contrast, 1.25); brightness += 4
    elif profile == 'Realce de trilhas':
        gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
        edges = cv2.detailEnhance(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), sigma_s=10, sigma_r=0.15)
        out = cv2.addWeighted(out, 0.65, edges, 0.35, 0)
    elif profile == 'Realce de solda':
        out = cv2.detailEnhance(out, sigma_s=12, sigma_r=0.18)
    elif profile == 'Detecção de bordas':
        gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY); edges = cv2.Canny(gray, 70, 150); out = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    out = cv2.convertScaleAbs(out, alpha=float(contrast), beta=int(brightness))
    if saturation != 1.0:
        hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32); hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation, 0, 255); out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    if gamma != 1.0:
        table = np.array([((i / 255.0) ** (1.0 / max(gamma, 0.1))) * 255 for i in np.arange(256)]).astype('uint8'); out = cv2.LUT(out, table)
    if sharpness > 0:
        blur = cv2.GaussianBlur(out, (0, 0), 1.2); out = cv2.addWeighted(out, 1.0 + sharpness, blur, -sharpness, 0)
    return out
