"""Where the pipeline reads and writes.

``outputs/`` sits beside ``src/`` at the repository root:

- ``raw/``      fetched source archives, gitignored, restored by ``article-data fetch``
- ``inputs/``   committed pinned inputs for sources that cannot be re-fetched byte-for-byte
- ``computed/`` outputs; small ones are committed as fixtures, large ones are gitignored
- ``exhibits/`` the article charts, SVGs regenerated from ``computed/`` and committed
"""

from pathlib import Path

OUTPUTS = Path(__file__).resolve().parents[2] / "outputs"
RAW = OUTPUTS / "raw"
INPUTS = OUTPUTS / "inputs"
COMPUTED = OUTPUTS / "computed"
EXHIBITS = OUTPUTS / "exhibits"
