mkdir -p /root/.sbws/logs

crontab -l | { cat; echo "*/5 * * * * /usr/local/bin/sbws -c /root/.sbws.ini generate >> /root/.sbws/logs/generate.log  2>&1"; } | crontab -
crontab -l | { cat; echo "30  0 * * * /usr/local/bin/sbws -c /root/.sbws.ini cleanup >> /root/.sbws/logs/cleanup.log  2>&1"; } | crontab -

sbws scanner
