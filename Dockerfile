FROM ubuntu:latest
LABEL authors="super"

ENTRYPOINT ["top", "-b"]