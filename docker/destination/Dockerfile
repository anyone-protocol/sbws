FROM nginx

WORKDIR /app/destination

COPY docker-entrypoint.sh /app/destination

#COPY default.conf /etc/nginx/conf.d/default.conf

ENTRYPOINT [ "sh", "docker-entrypoint.sh" ]
