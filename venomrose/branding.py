"""VENOMROSE branding. The original approved PNG is embedded unchanged in portable reports."""
import base64
from functools import lru_cache
from pathlib import Path

ARTWORK = Path(__file__).resolve().parent.parent / 'assets' / 'venomrose-command-center-ORIGINAL.png'
REPOSITORY = 'https://github.com/Hellfire13666/venomrose-proxy-foundry-2026'

@lru_cache(maxsize=1)
def embedded_banner() -> str:
    """Return a full-resolution PNG data URI. Never fetch images from the internet."""
    return 'data:image/png;base64,' + base64.b64encode(ARTWORK.read_bytes()).decode('ascii')
