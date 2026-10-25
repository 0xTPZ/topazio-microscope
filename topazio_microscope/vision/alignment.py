from dataclasses import dataclass, field

import cv2
import numpy as np


def _gray(frame: np.ndarray) -> np.ndarray:
    return frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


@dataclass
class AlignmentResult:
    image: np.ndarray
    success: bool
    keypoints: int = 0
    matches: int = 0
    inliers: int = 0
    message: str = ''

    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'keypoints': self.keypoints,
            'matches': self.matches,
            'inliers': self.inliers,
            'message': self.message,
        }


@dataclass
class ComparisonResult:
    overlay: np.ndarray
    difference: np.ndarray
    aligned: np.ndarray
    changed_ratio: float
    mean_difference: float
    alignment: AlignmentResult
    alpha: float = 0.5

    def to_dict(self) -> dict:
        return {
            'changed_ratio': round(float(self.changed_ratio), 6),
            'mean_difference': round(float(self.mean_difference), 4),
            'alpha': self.alpha,
            'alignment': self.alignment.to_dict(),
        }


def align_images_orb(reference: np.ndarray, moving: np.ndarray, max_features: int = 1200) -> AlignmentResult:
    """Alinha uma imagem à referência usando ORB + RANSAC quando há pontos suficientes."""
    if reference is None or moving is None or reference.size == 0 or moving.size == 0:
        return AlignmentResult(moving, False, message='Imagens vazias')
    orb = cv2.ORB_create(nfeatures=max_features)
    key_ref, desc_ref = orb.detectAndCompute(_gray(reference), None)
    key_mov, desc_mov = orb.detectAndCompute(_gray(moving), None)
    keypoint_count = min(len(key_ref or []), len(key_mov or []))
    if desc_ref is None or desc_mov is None or keypoint_count < 4:
        return AlignmentResult(moving.copy(), False, keypoint_count, message='Pontos locais insuficientes para ORB')
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    pairs = matcher.knnMatch(desc_mov, desc_ref, k=2)
    good = [first for first, second in pairs if first.distance < 0.75 * second.distance]
    if len(good) < 4:
        return AlignmentResult(moving.copy(), False, keypoint_count, len(good), message='Correspondências insuficientes para RANSAC')
    source = np.float32([key_mov[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    target = np.float32([key_ref[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    homography, mask = cv2.findHomography(source, target, cv2.RANSAC, 5.0)
    if homography is None or mask is None:
        return AlignmentResult(moving.copy(), False, keypoint_count, len(good), message='RANSAC não encontrou transformação')
    height, width = reference.shape[:2]
    aligned = cv2.warpPerspective(moving, homography, (width, height))
    inliers = int(mask.ravel().sum())
    return AlignmentResult(aligned, True, keypoint_count, len(good), inliers, 'Alinhamento ORB/RANSAC aplicado')


def overlay_images(base: np.ndarray, other: np.ndarray, alpha: float = 0.5) -> np.ndarray:
    if base is None or other is None:
        raise ValueError('As duas imagens são necessárias para sobreposição')
    height, width = base.shape[:2]
    resized = cv2.resize(other, (width, height), interpolation=cv2.INTER_AREA)
    alpha = float(max(0.0, min(1.0, alpha)))
    return cv2.addWeighted(base, 1.0 - alpha, resized, alpha, 0.0)


def compare_images(reference: np.ndarray, candidate: np.ndarray, alpha: float = 0.5,
                   align: bool = False) -> ComparisonResult:
    alignment = align_images_orb(reference, candidate) if align else AlignmentResult(candidate.copy(), False, message='Alinhamento não solicitado')
    aligned = alignment.image if alignment.image.shape[:2] == reference.shape[:2] else cv2.resize(alignment.image, (reference.shape[1], reference.shape[0]))
    base_gray = _gray(reference).astype(np.int16)
    candidate_gray = _gray(aligned).astype(np.int16)
    difference = np.abs(base_gray - candidate_gray).astype(np.uint8)
    threshold = max(12, int(float(difference.mean()) + 2.0 * float(difference.std())))
    changed_ratio = float(np.count_nonzero(difference >= threshold) / difference.size)
    return ComparisonResult(overlay_images(reference, aligned, alpha), difference,
                            aligned, changed_ratio, float(difference.mean()), alignment, float(alpha))
