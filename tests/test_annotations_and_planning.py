import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
from topazio_microscope.inspection.annotations import Annotation, AnnotationModel

def test_annotation_layers_coordinates_and_roundtrip():
    model=AnnotationModel(); model.add(Annotation('line', [[10.5, 20.25], [90.0, 120.75]], '#d9aa3a', 3, '', 'Planejamento'))
    path=Path(tempfile.gettempdir())/'topazio_v02_annotations.json'; model.save(path)
    loaded=AnnotationModel(); loaded.load(path)
    assert loaded.items[0].points == [[10.5, 20.25], [90.0, 120.75]]
    assert loaded.items[0].layer == 'Planejamento'
    loaded.undo(); loaded.redo(); assert len(loaded.items) == 1
