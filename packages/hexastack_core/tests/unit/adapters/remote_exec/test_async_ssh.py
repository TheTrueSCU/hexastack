"""Unit tests for AsyncSshAdapter.

Notes/Architectural Intent:
    Tests AsyncSshAdapter command preparation, connection management, execution, streaming,
    and SFTP file operations using hermetic test doubles and mock asyncssh channels.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hexastack_core.adapters.remote_exec.async_ssh import AsyncSshAdapter


def test_async_ssh_import_error_message() -> None:
    """Validate clear ImportError when asyncssh is not installed."""
    adapter = AsyncSshAdapter(host="remote.cluster.internal")
    with patch(
        "builtins.__import__", side_effect=ImportError("No module named 'asyncssh'")
    ):
        with pytest.raises(ImportError) as exc_info:
            adapter._get_asyncssh()
        err_msg = str(exc_info.value)
        assert "The 'asyncssh' package is required" in err_msg


def test_prepare_command_with_env_and_cwd() -> None:
    """Validate that environment variables and working directory are escaped and prepended."""
    adapter = AsyncSshAdapter(host="node01")
    cmd = adapter._prepare_command(
        "python script.py",
        env={"CLUSTER_NAME": "hpc-01", "FLAG": 'quoted "val"'},
        cwd="/var/app",
    )
    assert "export CLUSTER_NAME=" in cmd
    assert "export FLAG=" in cmd
    assert "cd /var/app" in cmd
    assert cmd.endswith("python script.py")

    # Verify invalid environment variable key raises ValueError
    with pytest.raises(ValueError, match="Invalid environment variable name"):
        adapter._prepare_command("ls", env={"INVALID-KEY; rm -rf /": "val"})

    # Verify malicious cwd is escaped safely
    cmd_injection = adapter._prepare_command("ls", cwd="/var/app; whoami")
    assert (
        "cd '/var/app; whoami'" in cmd_injection
        or 'cd "/var/app; whoami"' in cmd_injection
    )


@pytest.mark.asyncio
async def test_run_command_success() -> None:
    """Validate successful remote command execution via mocked connection."""
    mock_result = MagicMock(exit_status=0, stdout="success\n", stderr="")
    mock_conn = AsyncMock()
    mock_conn.run = AsyncMock(return_value=mock_result)

    adapter = AsyncSshAdapter(host="node01", connection=mock_conn)
    res = await adapter.run("echo hello", timeout_seconds=15.0)

    exit_code = res.exit_status
    stdout = res.stdout
    stderr = res.stderr
    duration = res.duration_ms

    assert exit_code == 0
    assert stdout == "success\n"
    assert stderr == ""
    assert duration >= 0.0

    mock_conn.run.assert_awaited_once_with("echo hello", timeout=15.0, check=False)


@pytest.mark.asyncio
async def test_stream_output() -> None:
    """Validate asynchronous stdout streaming via create_process."""
    mock_process = AsyncMock()
    # Simulate stdout.read returning 2 chunks then empty string
    mock_process.stdout.read = AsyncMock(side_effect=["chunk 1 ", "chunk 2\n", ""])

    mock_conn = MagicMock()
    mock_conn.create_process.return_value.__aenter__ = AsyncMock(
        return_value=mock_process
    )
    mock_conn.create_process.return_value.__aexit__ = AsyncMock(return_value=None)

    adapter = AsyncSshAdapter(host="node01", connection=mock_conn)

    chunks: list[str] = []
    async for chunk in adapter.stream_output("stream-cmd"):
        chunks.append(chunk)

    assert chunks == ["chunk 1 ", "chunk 2\n"]


@pytest.mark.asyncio
async def test_upload_and_download_file(tmp_path: Path) -> None:
    """Validate SFTP upload and download methods."""
    local_src = tmp_path / "upload_src.bin"
    local_src.write_bytes(b"sample bytes")

    mock_sftp = AsyncMock()
    mock_sftp.put = AsyncMock()
    mock_sftp.get = AsyncMock()

    mock_conn = MagicMock()
    mock_conn.start_sftp_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_sftp
    )
    mock_conn.start_sftp_client.return_value.__aexit__ = AsyncMock(return_value=None)

    adapter = AsyncSshAdapter(host="node01", connection=mock_conn)

    # Upload
    await adapter.upload_file(str(local_src), "/remote/dest.bin")
    mock_sftp.put.assert_awaited_once_with(str(local_src), "/remote/dest.bin")

    # Download
    local_dest = tmp_path / "downloaded.bin"
    await adapter.download_file("/remote/dest.bin", str(local_dest))
    mock_sftp.get.assert_awaited_once_with("/remote/dest.bin", str(local_dest))

    # Missing local upload file
    with pytest.raises(FileNotFoundError):
        await adapter.upload_file(str(tmp_path / "missing.bin"), "/remote/missing.bin")


@pytest.mark.asyncio
async def test_connection_lifecycle_and_context_manager() -> None:
    """Validate context manager connection open and close."""
    mock_conn = AsyncMock()
    mock_conn.close = MagicMock()
    mock_conn.wait_closed = AsyncMock()

    mock_asyncssh = MagicMock()
    mock_asyncssh.connect = AsyncMock(return_value=mock_conn)

    adapter = AsyncSshAdapter(host="node01")
    adapter._get_asyncssh = MagicMock(return_value=mock_asyncssh)

    async with adapter:
        active_conn = await adapter.get_connection()
        assert active_conn == mock_conn

    mock_conn.close.assert_called_once()
    mock_conn.wait_closed.assert_awaited_once()
    assert adapter._connection is None
