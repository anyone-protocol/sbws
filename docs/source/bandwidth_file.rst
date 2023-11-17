.. _bandwidth_file:

``BandwidthFile`` modifications
===============================

Code to modify when a new ``KeyValue`` is added
-----------------------------------------------

In the case of a ``KeyValue`` that comes from the configuration file::

    docs/source/config.example.ini
    docs/source/examples/sbws.example.ini
    sbws/config.default.ini
    sbws/core/generate.py
    sbws/globals.py
    sbws/lib/v3bwfile.py
    sbws/util/config.py
    tests/integration/sbws_testnet.ini
    tests/unit/lib/test_v3bwfile.py
    tests/unit/util/test_config.py

Other repositories that need to be modified:

- `Tor specifications`_: `bandwidth-file-spec`_
- `descriptorParser`_: `BandwidthParser.java`_
- `Metrics SQL Tables`_: `bandwidth_tables.sql`_

.. _bandwidth_tables.sql: https://gitlab.torproject.org/tpo/network-health/metrics/metrics-sql-tables/-/blob/95bb0e657f8c86e3bc92ca44273e92b1899052ee/bandwidth_tables.sql
.. _bandwidth-file-spec: https://gitlab.torproject.org/tpo/core/torspec/-/tree/main/spec/bandwidth-file-spec
.. _BandwidthParser.java: https://gitlab.torproject.org/tpo/network-health/metrics/descriptorParser/-/blob/d23f0209370563be1a015abd4702bc02b8ef7427/src/main/java/org/torproject/metrics/descriptorparser/parsers/BandwidthParser.java
.. _descriptorParser: https://gitlab.torproject.org/tpo/network-health/metrics/descriptorParser
.. _Metrics SQL Tables: https://gitlab.torproject.org/tpo/network-health/metrics/metrics-sql-tables
.. _Tor specifications: https://gitlab.torproject.org/tpo/core/torspec
