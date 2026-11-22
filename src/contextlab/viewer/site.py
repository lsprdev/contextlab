"""Gera o site de documentação: `python -m contextlab.viewer.site PASTA`."""
from __future__ import annotations

import sys
from pathlib import Path

from . import build_site


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    destination = Path(args[0] if args else "site-dist")
    experiment = Path(args[1]) if len(args) > 1 else None
    print(f"Site gerado em {build_site(destination, experiment=experiment)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
