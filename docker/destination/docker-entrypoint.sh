mkdir -p data/index && cd data/index

head -c $((1024*1024*1024)) /dev/urandom > 1GiB

chmod 777 1GiB

nginx -g 'daemon off;'
