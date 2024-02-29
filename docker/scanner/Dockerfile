FROM debian:bookworm

RUN apt update && \
    DEBIAN_FRONTEND=noninteractive apt install -y \
    python3-dateutil python3-stem pip cron

WORKDIR /app/scanner

ADD ../.. /app/scanner/temp

RUN cd temp && ls -la && \
    pip install . --break-system-packages && \
    cp docker/scanner/docker-entrypoint.sh .. && \
    cd .. && \
    rm -rf temp

RUN apt-get -y update && \
    apt-get -y install wget apt-transport-https && \
    . /etc/os-release && \
    wget -qO- https://deb.dmz.ator.dev/anon.asc | tee /etc/apt/trusted.gpg.d/anon.asc && \
    echo "deb [signed-by=/etc/apt/trusted.gpg.d/anon.asc] https://deb.dmz.ator.dev anon-dev-$VERSION_CODENAME main" > /etc/apt/sources.list.d/anon.list && \
    apt-get -y update && \
    apt-get -y install anon

ENTRYPOINT [ "sh", "docker-entrypoint.sh" ]
