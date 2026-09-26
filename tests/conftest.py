"""Shared fixtures for FuselageFEM tests."""

import sys
from pathlib import Path

# Add the project root to sys.path so tests can import modules
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
