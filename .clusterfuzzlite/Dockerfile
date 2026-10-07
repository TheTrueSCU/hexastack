FROM gcr.io/oss-fuzz-base/base-builder-python

# Install astral uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY . $SRC/hexastack
WORKDIR $SRC/hexastack

# Ensure Python 3.13 is installed and sync the full workspace environment with uv
RUN uv python install 3.13 && \
    uv sync --frozen && \
    uv pip install pyinstaller

# Activate virtual environment for pyinstaller and compile_python_fuzzer
ENV PATH="$SRC/hexastack/.venv/bin:$PATH"
ENV VIRTUAL_ENV="$SRC/hexastack/.venv"

COPY .clusterfuzzlite/build.sh $SRC/
