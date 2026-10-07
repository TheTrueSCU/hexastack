FROM gcr.io/oss-fuzz-base/base-builder-python@sha256:f606cee856c34585c314af4fbc41940bce398f5244fbfc757116188828f473c6

# Install astral uv binary
COPY --from=ghcr.io/astral-sh/uv@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21 /uv /bin/uv

COPY . $SRC/hexastack
WORKDIR $SRC/hexastack

# Ensure Python 3.13 is installed and sync the full workspace environment with uv
RUN uv python install 3.13 && \
    uv sync --frozen && \
    uv pip install pyinstaller grpcio-tools

# Activate virtual environment for pyinstaller and compile_python_fuzzer
ENV PATH="$SRC/hexastack/.venv/bin:$PATH"
ENV VIRTUAL_ENV="$SRC/hexastack/.venv"
ENV PYDANTIC_DISABLE_PLUGINS=1

COPY .clusterfuzzlite/build.sh $SRC/
