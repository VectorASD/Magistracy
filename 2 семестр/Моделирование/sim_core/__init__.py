import sys
from pathlib import Path
path = str(Path(__file__).resolve().parent)
if path not in sys.path:
    sys.path.insert(0, path)

from . import des
from . import rnd
from . import blocks

del sys, Path, path
