FROM gcr.io/oss-fuzz-base/base-builder-python

# Install astral uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install runtime dependencies required by fuzz harnesses into system environment
RUN uv pip install --system \
    grpcio-tools \
    hexaflow \
    openfeature-sdk \
    pydantic \
    rodi \
    stamina \
    tenacity

COPY . $SRC/hexastack
WORKDIR $SRC/hexastack

# Install workspace packages without transitive extras using uv
RUN uv pip install --system --no-deps packages/*

# Provide fallback PYTHONPATH for fuzz harness runner wrappers
ENV PYTHONPATH="/src/hexastack/packages/hexastack_ai/src:\
/src/hexastack/packages/hexastack_auth/src:\
/src/hexastack/packages/hexastack_cli/src:\
/src/hexastack/packages/hexastack_core/src:\
/src/hexastack/packages/hexastack_cqrs/src:\
/src/hexastack/packages/hexastack_db/src:\
/src/hexastack/packages/hexastack_events/src:\
/src/hexastack/packages/hexastack_fastapi/src:\
/src/hexastack/packages/hexastack_flags/src:\
/src/hexastack/packages/hexastack_flow/src:\
/src/hexastack/packages/hexastack_graphql/src:\
/src/hexastack/packages/hexastack_grpc/src:\
/src/hexastack/packages/hexastack_logging/src:\
/src/hexastack/packages/hexastack_mcp/src:\
/src/hexastack/packages/hexastack_otel/src:\
/src/hexastack/packages/hexastack_qual/src:\
/src/hexastack/packages/hexastack_ui/src:\
/src/hexastack/packages/hexastack/src:\
$PYTHONPATH"

COPY .clusterfuzzlite/build.sh $SRC/
