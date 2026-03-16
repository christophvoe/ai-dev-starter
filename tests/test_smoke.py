"""
Smoke test — verifies the project is importable and main() runs.
"""
import importlib
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_main_importable():
    mod = importlib.import_module("main")
    assert hasattr(mod, "main")


def test_main_runs():
    from main import main
    main()  # Should not raise
