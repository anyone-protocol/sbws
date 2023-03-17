Troubleshooting
===============

known bugs.

json.decoder.JSONDecodeError
----------------------------

This error occurs when the ``state.dat`` JSON file is malformed.

The way to work around this error is to delete the file or manually delete
the lines that do not conform to the JSON syntax and restart the processes.

Known reasons why ``state.dat`` may be malformed are:

* power outage
* disk full

Both cases can cause either the ``scanner`` or the ``generator`` not to
finish writing proper JSON lines to the file, since this operation is not
atomic.

This error does not happen in the next scanner version because is using a
database that support atomic operations.

More information about this bug at: 40153_, 40077_, 40020_.

.. _40153: https://gitlab.torproject.org/tpo/network-health/sbws/-/issues/40153
.. _40077: https://gitlab.torproject.org/tpo/network-health/sbws/-/issues/40077
.. _40020: https://gitlab.torproject.org/tpo/network-health/sbws/-/issues/40020
