from datetime import datetime
from pathlib import Path
import os

def capture_root() -> Path:
    """Return a user-writable capture directory without depending on the install folder."""
    override = os.environ.get('TOPAZIO_CAPTURE_DIR')
    if override:
        root = Path(override).expanduser()
    else:
        root = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'TopazioLabs' / 'TopazioMicroscope' / 'captures'
    root.mkdir(parents=True, exist_ok=True)
    return root

def session_root() -> Path:
    root = capture_root() / datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    root.mkdir(parents=True, exist_ok=True)
    return root
