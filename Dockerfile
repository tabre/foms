FROM debian:latest

ENV PATH="$PATH:/root/.local/bin"

RUN apt update && apt install -y curl ca-certificates

RUN mkdir -p /root/foms/static/js
WORKDIR /root/foms

RUN curl -LsSf https://astral.sh/uv/install.sh | sh && test -x /root/.local/bin/uv
