mkdir -p /app/scanner/data/logs

crontab -l | { cat; echo "*/5 * * * * sbws generate >> /app/scanner/data/logs/generate.log  2>&1"; } | crontab -
crontab -l | { cat; echo "30  0 * * * sbws cleanup >> /app/scanner/data/logs/cleanup.log  2>&1"; } | crontab -

cron -f
