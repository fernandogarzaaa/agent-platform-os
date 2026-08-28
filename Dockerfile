FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/var/cache/uv

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.5.31

RUN useradd --create-home --uid 10001 platform
WORKDIR /platform

COPY pyproject.toml README.md ./
COPY agent_platform_os ./agent_platform_os
COPY scripts ./scripts

RUN uv pip install --system --no-cache . \
    && mkdir -p /workspace /var/cache/uv \
    && chown -R platform:platform /workspace /var/cache/uv /platform

EXPOSE 8080

# Starts as root: a real deployment bind-mounts a service checkout (cloned by
# whatever host user ran scripts/bootstrap_services.py) over /workspace, which
# won't be owned by this image's fixed platform uid. run_service.py fixes that
# mount's ownership, then drops privileges to platform before doing anything
# else -- this container never runs application code as root.
ENTRYPOINT ["python", "/platform/scripts/run_service.py"]
