from scripts.validate_creator_registry_consolidation import pytest_summary


def _log(error_count: int, root: str, digest: str) -> str:
    return f"""============================= test session starts ==============================
=================================== FAILURES ===================================
____________________________ test_release_gate _____________________________

>       assert validate_release() is True
E       AssertionError: release validation failed at {root}
E       assert False is True
---------------------------- Captured stdout call -----------------------------
VALIDATION FAILED with {error_count} errors:
  - Deterministic content hash mismatch: expected sha256_{digest}, got sha256_{digest}
=========================== short test summary info ============================
FAILED tests/test_release.py::test_release_gate
========================= 1 failed, 10 passed in 1.00s =========================
"""


def test_pytest_failure_signature_detects_worsened_known_failure():
    baseline = pytest_summary(
        _log(4, "C:\\Users\\Icezaza\\ThaiVtuberSNA", "a" * 64)
    )
    current = pytest_summary(
        _log(19, "/home/runner/work/ThaiVtuberSNA/ThaiVtuberSNA", "b" * 64)
    )

    nodeid = "tests/test_release.py::test_release_gate"
    assert baseline["failure_details"][nodeid]["exception_class"] == "AssertionError"
    assert (
        baseline["failure_details"][nodeid]["signature"]
        != current["failure_details"][nodeid]["signature"]
    )


def test_pytest_failure_signature_normalizes_paths_and_hashes():
    windows = pytest_summary(
        _log(4, "C:\\Users\\Icezaza\\ThaiVtuberSNA", "a" * 64)
    )
    linux = pytest_summary(
        _log(4, "/home/runner/work/ThaiVtuberSNA/ThaiVtuberSNA", "b" * 64)
    )

    nodeid = "tests/test_release.py::test_release_gate"
    assert (
        windows["failure_details"][nodeid]["signature"]
        == linux["failure_details"][nodeid]["signature"]
    )


def test_pytest_summary_treats_collection_errors_as_blockers():
    summary = pytest_summary(
        """============================= ERRORS ====================================
ERROR tests/test_broken.py
====================== 3 passed, 1 error in 0.10s ======================
"""
    )
    assert summary["error_tests"] == ["tests/test_broken.py"]
    assert summary["errors"] == 1
