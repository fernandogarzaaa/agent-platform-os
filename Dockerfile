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

USER platform
EXPOSE 8080

ENTRYPOINT ["python", "/platform/scripts/run_service.py"]
