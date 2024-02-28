FROM nginx

WORKDIR /app/destination

COPY docker-entrypoint.sh /app/destination

ENTRYPOINT [ "sh", "docker-entrypoint.sh" ]
