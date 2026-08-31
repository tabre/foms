FROM debian:bookworm-slim

RUN apt update && apt install -y curl ca-certificates

ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} appuser && useradd -m -u ${UID} -g ${GID} appuser

USER appuser
ENV HOME=/home/appuser

RUN mkdir /home/appuser/foms

WORKDIR $HOME/foms

ENV PATH="$PATH:$HOME/.local/bin"

RUN mkdir -p static/js

RUN curl -LsSf https://astral.sh/uv/install.sh | sh && test -x "$HOME/.local/bin/uv"
