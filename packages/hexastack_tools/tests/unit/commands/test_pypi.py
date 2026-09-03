from pathlib import Path
from unittest.mock import patch

import pytest

from hexastack_tools.commands.pypi import (
    build_main,
    check_main,
    publish_main,
)


def test_pypi_callables() -> None:
    """Verify pypi distribution callables."""
    assert callable(build_main)
    assert callable(check_main)
    assert callable(publish_main)


def test_build_main_custom_out_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify build_main parses --out-dir correctly."""
    monkeypatch.setattr("sys.argv", ["pypi-build", "--out-dir", "custom_dist"])
    with patch("hexastack_tools.commands.pypi.build_all_packages") as mock_build:
        mock_build.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            build_main()
        assert exc_info.value.code == 0
        mock_build.assert_called_once_with(out_dir=Path("custom_dist"))
