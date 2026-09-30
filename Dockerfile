# Docker in this repo is only supported for running tests locally
# as an alternative to virtualenv natively
FROM ubuntu:noble as app
MAINTAINER sre@edx.org


# Packages installed:
# git; Used to pull in particular requirements from github rather than pypi,
# and to check the sha of the code checkout.

# build-essentials; so we can use make with the docker container

# language-pack-en locales; ubuntu locale support so that system utilities have a consistent
# language and time zone.

# python; ubuntu doesnt ship with python, so this is the python we will use to run the application

# python3-pip; install pip to install application requirements.txt files

# pkg-config
#     mysqlclient>=2.2.0 requires this (https://github.com/PyMySQL/mysqlclient/issues/620)

# libmysqlclient-dev; to install header files needed to use native C implementation for
# MySQL-python for performance gains.

# libssl-dev; # mysqlclient wont install without this.

# python3-dev; to install header files for python extensions; much wheel-building depends on this

# gcc; for compiling python extensions distributed with python packages like mysql-client

# If you add a package here please include a comment above describing what it is used for
RUN apt-get update && apt-get -qy install --no-install-recommends \
 language-pack-en \
 locales \
 python3.12 \
 python3-pip \
 python3.12-venv \
 pkg-config \
 libmysqlclient-dev \
 libssl-dev \
 python3-dev \
 gcc \
 build-essential \
 git \
 curl


# No system-wide `pip install --upgrade pip setuptools` here: on 24.04,
# python3-pip is a debian-packaged pip that pip itself cannot cleanly
# uninstall/upgrade in place (and PEP 668 blocks touching it without
# --break-system-packages anyway). Nothing runs against this system Python --
# the venv created below gets its own pip, and that's what everything else
# in this image uses.
# delete apt package lists because we do not need them inflating our image
RUN rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python3 /usr/bin/python

RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8
ENV DJANGO_SETTINGS_MODULE enterprise.settings.test

# Env vars: path
ENV VIRTUAL_ENV='/edx/app/venvs/openedx-ledger'
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PATH="/edx/app/openedx-ledger/node_modules/.bin:${PATH}"
ENV PATH="/edx/app/openedx-ledger/bin:${PATH}"
ENV PATH="/edx/app/nodeenv/bin:${PATH}"

RUN useradd -m --shell /bin/false app

WORKDIR /edx/app/openedx-ledger

RUN python3.12 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy the lockfile explicitly even though we copy everything below
# this prevents the image cache from busting unless the dependencies have changed.
COPY pyproject.toml uv.lock /edx/app/openedx-ledger/

# Dependencies are installed as root so they cannot be modified by the application user.
# --no-install-project: only third-party deps at this point -- the local
# `openedx_ledger` package itself lives under src/ and can't be installed
# from just these two files, so it's installed separately below once the
# full source tree is present. This keeps this (slow, third-party) layer
# cached as long as pyproject.toml/uv.lock don't change.
RUN pip install uv
ENV UV_PROJECT_ENVIRONMENT=$VIRTUAL_ENV
RUN uv sync --locked --no-install-project --group dev
RUN pip install nodeenv

# Set up a Node environment and install Node requirements.
# Must be done after Python requirements, since nodeenv is installed
# via pip.
# The node environment is already 'activated' because its .../bin was put on $PATH.
RUN nodeenv /edx/app/nodeenv --node=20.17.0 --prebuilt

RUN mkdir -p /edx/var/log

# This line is after the dependency install so that unrelated code changes
# don't bust the third-party-dependency layer above, and it happens before
# the final `uv sync` (and before switching users) because that sync needs
# the full checkout to install the local `openedx_ledger` package from
# src/, and code/dependencies are installed as root so they cannot be
# modified by the application user.
COPY . /edx/app/openedx-ledger

# Install the local project itself now that its full source tree (src/) is
# present -- `[tool.setuptools.packages.find]`'s `where = ["src"]` picks it
# up automatically. This is fast: all third-party deps were already synced
# above, so this only adds the one local package. Trade-off versus the
# previous single-stage sync: this step (unlike the dependency layer above)
# reruns on every source change, since it has to -- the local package itself
# changed -- so source edits no longer get the full layer-cache benefit that
# a dependency-only change does.
RUN uv sync --locked --group dev

# Code is owned by root so it cannot be modified by the application user.
USER app

