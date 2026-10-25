"""Primitives de visão computacional local do Topázio Repair Assistant."""

from .metrics import ROI, crop_roi, detect_visual_suspicions, enhance_edges, sharpness_score
from .alignment import AlignmentResult, ComparisonResult, align_images_orb, compare_images, overlay_images

__all__ = [
    'ROI', 'crop_roi', 'detect_visual_suspicions', 'enhance_edges', 'sharpness_score',
    'AlignmentResult', 'ComparisonResult', 'align_images_orb', 'compare_images', 'overlay_images',
]
