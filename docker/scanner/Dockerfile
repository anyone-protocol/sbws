FROM debian:bookworm

RUN apt update && \
    DEBIAN_FRONTEND=noninteractive apt install -y \
    python3-dateutil python3-stem pip cron
#    pip install requests

WORKDIR /app/scanner

ADD ../.. /app/scanner/temp

RUN cd temp && ls -la && \
    pip install . --break-system-packages && \
    cp docker/scanner/docker-entrypoint.sh .. && \
    cd .. && \
    rm -rf temp

ENTRYPOINT [ "sh", "docker-entrypoint.sh" ]
