# syntax=docker/dockerfile:1

FROM fedora:latest
WORKDIR /app
COPY . .
# RUN dnf install -y lua luarocks
CMD ["python", "src/main.py"]