import logging

from hexastack_core.adapters.logging import StandardLogger


def test_standard_logger_custom_logger(caplog):
    std_logger = logging.getLogger("test_hexastack")
    adapter = StandardLogger(logger=std_logger)

    with caplog.at_level(logging.DEBUG, logger="test_hexastack"):
        adapter.debug("Debug msg")
        adapter.info("Info msg")
        adapter.warning("Warn msg")
        adapter.error("Error msg", exc=ValueError("test exc"))

    assert "Debug msg" in caplog.text
    assert "Info msg" in caplog.text
    assert "Warn msg" in caplog.text
    assert "Error msg" in caplog.text


def test_standard_logger_default_name():
    adapter = StandardLogger()
    assert adapter._logger.name == "hexastack"


def test_standard_logger_string_name():
    adapter = StandardLogger("custom_name")
    assert adapter._logger.name == "custom_name"
