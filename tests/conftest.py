"""pytest config: ensure project root is on sys.path so `scripts.aggregation` is importable."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
