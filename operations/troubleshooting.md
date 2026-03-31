# SBWS Operations Troubleshooting

## or-port healthcheck network issues

Check mapped ports, there should only be 1 tcp and 1 udp entry for the mapped or-port (i.e. 9291):
```bash
nft -a list chain nat CNI-HOSTPORT-DNAT
```

If there are multiple entries, determine which is the active one and delete the stale ones via their handle:
```bash
for h in 111 222 333 444; do
  sudo nft delete rule nat CNI-HOSTPORT-DNAT handle "$h"
done
```
