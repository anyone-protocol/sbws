#!/bin/bash
# Instead of exiting immediately when any of this commands fail,
# the scanner, generate and coverage lines could continue and store there was
# an error on that command. It's just simpler with `-e`.
set -ex

tests/integration/start_chutney.sh

sleep 60

python3 tests/integration/async_https_server.py &>/dev/null &
sleep 5
wget --no-check-certificate -O/dev/null https://localhost:28888/

# Run actually the scanner
sbws -c tests/integration/sbws_testnet.ini scanner
sbws -c tests/integration/sbws_testnet.ini generate
# Run integration tests
python -m coverage run --append --module pytest -svv tests/integration

sbws -c tests/integration/sbws_testnet.ini cleanup
tests/integration/stop_chutney.sh
