FROM gitpod/workspace-full

USER gitpod

# Install custom tools, runtimes, etc.
# For example "bastet", a command-line tetris clone:
# RUN brew install bastet
#
# More information: https://www.gitpod.io/docs/config-docker/

ARG DEBIAN_FRONTEND=noninteractive

RUN sudo rm -rf /var/lib/apt/lists/* \
      && \
    sudo apt-get -q update \
      && \
    sudo apt-get install -y --no-install-recommends \
      apt-utils \
      && \
    sudo apt-get install -yq \
      libnspr4 \
      libnss3 \
      libnss3-tools \
      && \
    sudo apt-get -yq dist-upgrade \
      && \
    sudo rm -rf /var/lib/apt/lists/*

# set up a clean terminal prompt
RUN printf '%s\n' \
    "export PS1='\[\e]0;\u \w\a\]${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u\[\033[00m\] \[\033[01;34m\]\w \$ \[\033[00m\]'" \
    >> "$HOME/.bashrc"
