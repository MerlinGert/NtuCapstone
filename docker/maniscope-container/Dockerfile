FROM ubuntu:24.04

ARG MANISCOPE_UID=1000
ARG MANISCOPE_GID=1000

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8 \
    BUN_INSTALL=/usr/local \
    PLAYWRIGHT_BROWSERS_PATH=/home/maniscope/.cache/ms-playwright \
    UV_LINK_MODE=copy \
    PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    locales \
    tzdata \
    sudo \
    gosu \
    supervisor \
    nginx \
    git \
    zsh \
    build-essential \
    pkg-config \
    python3 \
    python3-venv \
    procps \
    iproute2 \
    net-tools \
    lsof \
    less \
    file \
    unzip \
    zip \
    rsync \
    ripgrep \
    fd-find \
    jq \
    yq \
    miller \
    sqlite3 \
    htop \
    tmux \
    tree \
    vim \
    nano \
    fonts-liberation \
    fonts-noto-color-emoji \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libgtk-3-0 \
    libasound2t64 \
    libatspi2.0-0 \
    libx11-xcb1 \
    && sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen \
    && ln -sf /usr/bin/fdfind /usr/local/bin/fd \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g npm@latest @openai/codex \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh \
    && curl -fsSL https://bun.sh/install | env BUN_INSTALL=/usr/local bash

RUN set -eux; \
    if getent group "${MANISCOPE_GID}" >/dev/null; then \
        EXISTING_GROUP="$(getent group "${MANISCOPE_GID}" | cut -d: -f1)"; \
        if [ "${EXISTING_GROUP}" != maniscope ]; then \
            groupmod --new-name maniscope "${EXISTING_GROUP}"; \
        fi; \
    else \
        groupadd --gid "${MANISCOPE_GID}" maniscope; \
    fi; \
    if getent passwd "${MANISCOPE_UID}" >/dev/null; then \
        EXISTING_USER="$(getent passwd "${MANISCOPE_UID}" | cut -d: -f1)"; \
        usermod --login maniscope "${EXISTING_USER}"; \
        usermod --home /home/maniscope --move-home maniscope; \
        usermod --gid maniscope --shell /usr/bin/zsh maniscope; \
    else \
        useradd --uid "${MANISCOPE_UID}" --gid maniscope -m -s /usr/bin/zsh maniscope; \
    fi; \
    echo 'maniscope ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/maniscope; \
    chmod 0440 /etc/sudoers.d/maniscope; \
    mkdir -p /workspace/NtuCapstone \
        /home/maniscope/.codex \
        /home/maniscope/.cache/uv \
        /home/maniscope/.cache/ms-playwright \
        /home/maniscope/.bun/install/cache; \
    chown -R maniscope:maniscope /workspace /home/maniscope

WORKDIR /workspace/NtuCapstone

COPY docker/maniscope-container/entrypoint.sh /opt/maniscope/entrypoint.sh
COPY docker/maniscope-container/supervisord-dev.conf /opt/maniscope/supervisord-dev.conf
COPY docker/maniscope-container/supervisord-study.conf /opt/maniscope/supervisord-study.conf
COPY docker/maniscope-container/nginx-study.conf /opt/maniscope/nginx-study.conf

RUN chmod 0755 /opt/maniscope/entrypoint.sh

EXPOSE 3099 8099 8787

ENTRYPOINT ["/opt/maniscope/entrypoint.sh"]
