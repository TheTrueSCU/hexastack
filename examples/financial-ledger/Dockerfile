# Multi-stage ultra-fast uv Dockerfile
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies in isolated layer
RUN --mount=type=cache,target=/root/.cache/uv     --mount=type=bind,source=uv.lock,target=uv.lock     --mount=type=bind,source=pyproject.toml,target=pyproject.toml     uv sync --frozen --no-install-project --no-dev

# Copy application source and build final virtualenv
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv     uv sync --frozen --no-dev

# Final rootless production runtime stage
FROM python:3.13-slim-bookworm AS runtime

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1

# Create non-root system user
RUN groupadd -r -g 10001 appuser &&     useradd -r -u 10001 -g appuser -d /app -s /sbin/nologin appuser

# Copy virtualenv and application from builder
COPY --from=builder --chown=appuser:appuser /app /app

USER appuser:appuser
EXPOSE 8000 50051

HEALTHCHECK --interval=10s --timeout=3s --retries=3     CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["financial-ledger"]
CMD ["dev"]
