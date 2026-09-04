from typing import Literal

from pydantic import BaseModel, Field

_DEFAULT_MASKED_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "authorization",
    "client_secret",
    "password",
    "refresh_token",
    "secret",
    "token",
}

_DEFAULT_PATTERNS = [
    r"Bearer\s+[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]+",
    r"(sk-[A-Za-z0-9]{20,})",
    r"(ghp_[A-Za-z0-9]{36})",
]


class FileLoggingConfig(BaseModel):
    """Configuration schema for file-based logging and log rotation.

    Notes/Architectural Intent:
        Controls disk log writing, rotation triggers (size vs. time intervals),
        retention backup counts, and destination file paths.
    """

    enable: bool = Field(default=False)
    path: str = Field(default="logs/app.log")
    format: Literal["console", "json"] = Field(default="json")
    max_bytes: int = Field(default=10_485_760)  # 10 MB
    backup_count: int = Field(default=5)
    rotation_type: Literal["size", "time"] = Field(default="size")
    when: str = Field(default="midnight")


class AsyncQueueConfig(BaseModel):
    """Configuration schema for non-blocking queue-based background log emission.

    Notes/Architectural Intent:
        Offloads disk and stream I/O from request worker threads and async event loops
        to a dedicated background worker thread using QueueHandler and QueueListener.
    """

    enable: bool = Field(default=False)
    max_size: int = Field(default=10_000)


class SanitizerConfig(BaseModel):
    """Configuration schema for log sanitization and credential masking.

    Notes/Architectural Intent:
        Controls automatic redaction of sensitive dictionary keys and regex pattern matches.
    """

    enable: bool = Field(default=True)
    masked_keys: list[str] = Field(default_factory=lambda: sorted(_DEFAULT_MASKED_KEYS))
    mask_replacement: str = Field(default="***REDACTED***")
    regex_patterns: list[str] = Field(default_factory=lambda: list(_DEFAULT_PATTERNS))


class HexastackLoggingConfig(BaseModel):
    """Configuration schema for application-wide logging.

    Notes/Architectural Intent:
        Controls log levels, output formatting (console vs. JSON), ANSI colorization,
        context propagation settings, data sanitization, file rotation, and async queueing.
    """

    level: str = Field(default="INFO")
    format: Literal["console", "json"] = Field(default="console")
    colorize: bool = Field(default=True)
    include_context: bool = Field(default=True)
    datefmt: str = Field(default="%Y-%m-%d %H:%M:%S")
    sanitizer: SanitizerConfig = Field(default_factory=SanitizerConfig)
    file: FileLoggingConfig = Field(default_factory=FileLoggingConfig)
    queue: AsyncQueueConfig = Field(default_factory=AsyncQueueConfig)
    loggers: dict[str, str] = Field(default_factory=dict)


__all__ = [
    "AsyncQueueConfig",
    "FileLoggingConfig",
    "HexastackLoggingConfig",
    "SanitizerConfig",
]
