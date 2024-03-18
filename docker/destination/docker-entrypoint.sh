mkdir -p data && cd data

head -c $((1024*1024*100)) /dev/urandom > 1GiB

nginx -g 'daemon off;'
