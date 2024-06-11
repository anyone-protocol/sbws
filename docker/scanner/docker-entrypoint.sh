mkdir -p /root/.sbws/log

cd /root/.sbws && rm -rf state.dat  state.dat.lockfile

crontab -l | { cat; echo "*/$INTERVAL_MINUTES * * * * export INTERVAL_MINUTES=$INTERVAL_MINUTES; /usr/local/bin/sbws -c /root/.sbws.ini generate >> /root/.sbws/log/generate.log  2>&1"; } | crontab -
crontab -l | { cat; echo "35  0 * * * /usr/local/bin/sbws -c /root/.sbws.ini cleanup >> /root/.sbws/log/cleanup.log  2>&1"; } | crontab -

service cron start

sbws scanner
