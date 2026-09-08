"""Retired destructive merge. Compatibility entry point performs a read-only policy audit."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.audit_private_data_plane import main

if __name__ == '__main__': sys.exit(main())
