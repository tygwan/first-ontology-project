"""Sanity checks for the config module."""

from bimkg import config


def test_project_root_contains_pyproject() -> None:
    assert (config.PROJECT_ROOT / "pyproject.toml").exists()


def test_data_raw_path_uses_current_snapshot() -> None:
    assert config.DATA_RAW.name == config.SNAPSHOT
    assert config.DATA_RAW.parent.name == "dxtnavis"


def test_expected_counts_are_positive() -> None:
    assert config.EXPECTED_OBJECT_COUNT == 12009
    assert config.EXPECTED_ADJACENCY_COUNT == 110173
    assert config.EXPECTED_CONNECTED_GROUPS == 3355
