import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

HEADER = "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1\n"


@pytest.fixture
def make_vcf(tmp_path):
    """Write a tiny VCF from data lines and return its path."""
    def _make(*lines: str, name: str = "t.vcf") -> Path:
        p = tmp_path / name
        p.write_text(HEADER + "\n".join(lines) + "\n")
        return p
    return _make
