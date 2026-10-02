"""Unit tests for InMemoryRemoteExecutionAdapter.

Notes/Architectural Intent:
    Verifies that the in-memory execution double accurately simulates remote command execution,
    stdout/stderr streaming, virtual filesystem uploads, and downloads.
"""

from pathlib import Path

import pytest

from hexastack_core.adapters.remote_exec.in_memory import InMemoryRemoteExecutionAdapter


@pytest.mark.asyncio
async def test_in_memory_run_registered_and_default_commands() -> None:
    """Validate that registered commands return custom outcomes and defaults fallback cleanly."""
    adapter = InMemoryRemoteExecutionAdapter(
        default_exit_status=1,
        default_stdout="default out",
        default_stderr="default err",
    )

    adapter.register_command(
        command="uname -a",
        exit_status=0,
        stdout="Linux cluster-node-01\n",
        stderr="",
        duration_ms=5.0,
    )

    res_reg = await adapter.run("uname -a")
    reg_exit = res_reg.exit_status
    reg_stdout = res_reg.stdout
    assert reg_exit == 0
    assert reg_stdout == "Linux cluster-node-01\n"

    res_def = await adapter.run("unknown_cmd")
    def_exit = res_def.exit_status
    def_stdout = res_def.stdout
    assert def_exit == 1
    assert def_stdout == "default out"

    history = adapter.executed_commands
    assert history == ["uname -a", "unknown_cmd"]


@pytest.mark.asyncio
async def test_in_memory_stream_output() -> None:
    """Validate streaming chunks for registered and unregistered commands."""
    adapter = InMemoryRemoteExecutionAdapter(default_stdout="stream_default")
    adapter.register_command(
        command="watch_logs",
        chunks=["line 1\n", "line 2\n", "line 3\n"],
    )

    chunks: list[str] = []
    async for chunk in adapter.stream_output("watch_logs"):
        chunks.append(chunk)

    assert chunks == ["line 1\n", "line 2\n", "line 3\n"]

    fallback_chunks: list[str] = []
    async for chunk in adapter.stream_output("other_cmd"):
        fallback_chunks.append(chunk)

    assert fallback_chunks == ["stream_default"]


@pytest.mark.asyncio
async def test_in_memory_upload_and_download_file(tmp_path: Path) -> None:
    """Validate virtual file upload and download operations."""
    adapter = InMemoryRemoteExecutionAdapter()

    local_src = tmp_path / "source.txt"
    local_src.write_bytes(b"payload content 12345")

    # Upload
    await adapter.upload_file(str(local_src), "/remote/virtual/data.txt")
    files = adapter.virtual_files
    assert "/remote/virtual/data.txt" in files
    assert files["/remote/virtual/data.txt"] == b"payload content 12345"

    # Download
    local_dest = tmp_path / "downloaded.txt"
    await adapter.download_file("/remote/virtual/data.txt", str(local_dest))
    read_bytes = local_dest.read_bytes()
    assert read_bytes == b"payload content 12345"

    # Missing local upload file
    with pytest.raises(FileNotFoundError):
        await adapter.upload_file(
            str(tmp_path / "non_existent.txt"), "/remote/missing.txt"
        )

    # Missing remote download file
    with pytest.raises(FileNotFoundError):
        await adapter.download_file(
            "/remote/non_existent.txt", str(tmp_path / "out.txt")
        )
