ARG BASE_IMAGE=debian:13
FROM ${BASE_IMAGE}

USER root

RUN set -eux; \
    if command -v apt-get >/dev/null 2>&1; then \
      apt-get update; \
      DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        bash ca-certificates curl wget tar coreutils findutils grep gawk git \
        python3 python3-venv python3-pip python3-dev build-essential \
        libssl-dev libffi-dev procps util-linux; \
      rm -rf /var/lib/apt/lists/*; \
    elif command -v dnf >/dev/null 2>&1; then \
      dnf install -y \
        bash ca-certificates curl wget tar coreutils findutils grep gawk git \
        python3 python3-pip python3-devel gcc openssl-devel libffi-devel \
        procps-ng util-linux shadow-utils; \
      dnf clean all; \
    else \
      echo 'Unsupported test base image: package manager not found' >&2; exit 1; \
    fi

RUN useradd --create-home --uid 1001 --user-group --shell /bin/bash nodecore \
    && install -d -o 1001 -g 1001 /workspace /home/nodecore/.node-core

ENV HOME=/home/nodecore
ENV USER=nodecore
ENV LOGNAME=nodecore
WORKDIR /workspace

USER 1001:1001
