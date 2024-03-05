mkdir -p /root/.sbws/log

crontab -l | { cat; echo "*/5 * * * * /usr/local/bin/sbws -c /root/.sbws.ini generate >> /root/.sbws/log/generate.log  2>&1"; } | crontab -
crontab -l | { cat; echo "30  0 * * * /usr/local/bin/sbws -c /root/.sbws.ini cleanup >> /root/.sbws/log/cleanup.log  2>&1"; } | crontab -

service cron start

sbws scanner
