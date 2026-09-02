"""Utilities for executing CLI tools and capturing cleaned help text in parallel."""

from __future__ import annotations

import collections
import concurrent.futures
import os
import re
import subprocess


def clean_help_output(output: str) -> str:
    """Strip ANSI escape sequences, warnings, and trailing whitespace from help text."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    clean = ansi_escape.sub("", output).strip()

    lines = clean.splitlines()
    filtered_lines: list[str] = []
    capture = False

    for line in lines:
        if (
            "Usage:" in line
            or "usage:" in line
            or capture
            or "╭─" in line
            or "Commands" in line
        ):
            capture = True
            filtered_lines.append(line.rstrip())

    final_lines = (
        filtered_lines if filtered_lines else [line.rstrip() for line in lines]
    )
    return "\n".join(final_lines)


def extract_command_help(cmd: list[str], timeout: int = 30) -> str:
    """Execute a command with --help and capture formatted text output."""
    env = dict(os.environ, NO_COLOR="1", TERM="dumb")
    try:
        res = subprocess.run(
            ["uv", "run"] + cmd + ["--help"],
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
        )
        raw = res.stdout if res.stdout.strip() else res.stderr
        return clean_help_output(raw)
    except subprocess.TimeoutExpired:
        try:
            res = subprocess.run(
                ["uv", "run"] + cmd + ["--help"],
                capture_output=True,
                text=True,
                env=env,
                timeout=60,
            )
            raw = res.stdout if res.stdout.strip() else res.stderr
            return clean_help_output(raw)
        except Exception as exc:
            return f"Error extracting help for '{' '.join(cmd)}': {exc}"
    except Exception as exc:
        return f"Error extracting help for '{' '.join(cmd)}': {exc}"


def extract_subcommands_from_help(help_text: str) -> list[str]:
    """Parse subcommand names from Typer/Rich formatted command tables."""
    subcommands: list[str] = []
    in_commands_block = False

    for line in help_text.splitlines():
        if "Commands" in line or "╭─ Commands" in line:
            in_commands_block = True
            continue
        if in_commands_block:
            if "╰─" in line:
                break
            match = re.search(r"│\s*([a-zA-Z0-9_\-]+)\s+", line)
            if match:
                subcommands.append(match.group(1))

    return subcommands


def extract_command_tree_bfs(
    root_cmd: list[str],
    max_workers: int = 8,
    timeout: int = 30,
) -> dict[tuple[str, ...], str]:
    """Traverse CLI command hierarchy using Breadth-First Search (BFS) in parallel."""
    results: dict[tuple[str, ...], str] = {}
    queue: collections.deque[list[str]] = collections.deque([root_cmd])

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        while queue:
            # Process the current breadth-level in parallel
            current_level_cmds: list[list[str]] = []
            while queue:
                current_level_cmds.append(queue.popleft())

            future_to_cmd = {
                executor.submit(extract_command_help, cmd, timeout): cmd
                for cmd in current_level_cmds
            }

            for future in concurrent.futures.as_completed(future_to_cmd):
                cmd = future_to_cmd[future]
                help_text = future.result()
                results[tuple(cmd)] = help_text

                # Discover next-level subcommands
                subcmds = extract_subcommands_from_help(help_text)
                for sub in subcmds:
                    # Guard against cyclical command discovery
                    child_cmd = cmd + [sub]
                    if tuple(child_cmd) not in results:
                        queue.append(child_cmd)

    return results


def extract_commands_parallel(
    cmd_list: list[list[str]],
    max_workers: int = 8,
    timeout: int = 30,
) -> dict[tuple[str, ...], str]:
    """Extract help text for a batch of independent commands in parallel."""
    results: dict[tuple[str, ...], str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_cmd = {
            executor.submit(extract_command_help, cmd, timeout): cmd for cmd in cmd_list
        }
        for future in concurrent.futures.as_completed(future_to_cmd):
            cmd = future_to_cmd[future]
            results[tuple(cmd)] = future.result()
    return results


__all__ = [
    "clean_help_output",
    "extract_command_help",
    "extract_command_tree_bfs",
    "extract_commands_parallel",
    "extract_subcommands_from_help",
]
