"""Compatibility alias for the documented local live command."""
import sys
from runner.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["run-live", *sys.argv[1:]]))
