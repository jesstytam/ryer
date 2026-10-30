# syntax=docker/dockerfile:1

FROM fedora:latest
WORKDIR /app
# RUN dnf install -y lua luarocks
# Qt needs these system libraries at runtime; the PyQt6 wheel does not bundle them
RUN dnf install -y \
    python3 \
    python3-pip \
    dbus-libs \
    fontconfig \
    glib2 \
    libxkbcommon \
    libxkbcommon-x11 \
    mesa-libEGL \
    mesa-libGL \
    xcb-util-cursor \
    xcb-util-image \
    xcb-util-keysyms \
    xcb-util-renderutil \
    xcb-util-wm
COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt
COPY . .
CMD ["python3", "src/main.py"]
