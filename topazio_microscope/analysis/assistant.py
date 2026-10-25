from dataclasses import dataclass

import cv2
import numpy as np

from ..vision.metrics import ROI, crop_roi, detect_visual_suspicions, enhance_edges, sharpness_score, highlight_suspicions


@dataclass
class AssistantAnalysis:
    roi: ROI | None
    sharpness: float
    edge_density: float
    mean_intensity: float
    suspicion_regions: list
    highlighted: np.ndarray
    edge_image: np.ndarray
    methods: list[str]
    warnings: list[str]

    def to_dict(self) -> dict:
        return {
            'roi': self.roi.to_dict() if self.roi else None,
            'sharpness': round(float(self.sharpness), 4),
            'edge_density': round(float(self.edge_density), 6),
            'mean_intensity': round(float(self.mean_intensity), 4),
            'suspicion_regions': [region.to_dict() for region in self.suspicion_regions],
            'methods': self.methods,
            'warnings': self.warnings,
        }


def analyze_frame(frame: np.ndarray, roi=None) -> AssistantAnalysis:
    if frame is None or frame.size == 0:
        raise ValueError('Não há imagem para analisar')
    crop, normalized = crop_roi(frame, roi)
    gray = crop if crop.ndim == 2 else cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 50, 150)
    edge_density = float(np.count_nonzero(edges) / max(1, edges.size))
    regions = detect_visual_suspicions(frame, normalized)
    highlighted = highlight_suspicions(frame, regions)
    return AssistantAnalysis(
        roi=normalized,
        sharpness=sharpness_score(frame, normalized),
        edge_density=edge_density,
        mean_intensity=float(np.mean(gray)),
        suspicion_regions=regions,
        highlighted=highlighted,
        edge_image=enhance_edges(frame, normalized),
        methods=['OpenCV', 'NumPy', 'heurística geométrica explícita'],
        warnings=[
            'Resultado visual auxiliar; não confirma continuidade ou rompimento elétrico.',
            'Valide qualquer hipótese com a placa desenergizada, esquema e multímetro.',
        ],
    )
