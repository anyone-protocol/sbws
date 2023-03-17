.. _deploy:

Deploying Simple Bandwidth Scanner
=====================================

To run sbws is needed:

- A machine to run the :term:`scanner`.
- One or more :term:`destination` (s) that serve a large file.

Both the ``scanner`` and your the ``destination`` (s) should be on fast,
well connected machines.

.. _destinations_requirements:

Destination requirements
------------------------

- TLS support to avoid HTTP content caches at the various exit nodes.
- Certificates can be self-signed.
- A fixed IP address or a domain name.
- Bandwidth: at least 12.5MB/s (100 Mbit/s).
- Network traffic: around 12-15GB/day.
- An HTTP Web server, see next subsection.

HTTP server requirements
~~~~~~~~~~~~~~~~~~~~~~~~

- If the consensus parameter ``bwscanner_cc`` is not set or has a value lower
  than 2:

  A Web server installed and running that supports HTTP GET, HEAD and
  Range (:rfc:`7233`) requests.
  ``Apache`` HTTP Server and ``Nginx`` support them.

  It also needs to allow ```keep-alive``, in order to reuse connections between
  the sbws HEAD request and the several GET ones.

  .. Note:: if the server is configured with ``keep-alive`` timeout, it'd need
     to be at least the same timeout as in the sbws HTTP requests, which is 10
     seconds by default (``http_timeout`` variable in the configuration file,
     see  more about in the next section).

  It also needs a large file; at the time of writing, at least 1 GiB in size
  It can be created running::

      head -c $((1024*1024*1024)) /dev/urandom > 1GiB

- If the consensus parameter ``bwscanner_cc`` has value 2:

  A Web server installed and running that supports HTTP POST either:

  - via ``Content-Type multipart/form-data`` (:rfc:`2388`) as a file upload.
  - via ``Content-Type multipart/form-data`` RFC 2388 as a raw (text) field
    upload.

  If your Web server supports HTTP MQTT binary but not the 2 previous methods,
  open an issue so that we implement the MQTT client part in the scanner.

Example configurations:

- Apache supporting HTTP GET and the three POST methods::

    <Location "/">
        AllowOverride None
        Order Deny,Allow
        Deny from All
    </Location>
    <Location "/1G">
            Allow from All
    </Location>
    <Location "/postpath">
            Allow from All
    </Location>

  And in the directory of static files served::

    head -c $((1024*1024*1024)) /dev/urandom > 1G
    echo OK > postpath

- nginx supporting the three POST methods::

    location /postpath {
      root /same/path/to/normal/directory;
      client_max_body_size 1G;
      # should not be necessary, but just in case nginx tries to litter:
      client_body_in_file_only clean;
      # this is a really horrible hack:
      error_page 405 =200 $uri;
    }

  And in the directory of static files served::

    echo OK > postpath

You can test your configuration running:

- HEAD request::

    curl https://bwauth.httpd.ip/1G -i -H "Range: bytes=0-1023"

  It should reply::

    HTTP/1.1 206 Partial Content
    Accept-Ranges: bytes
    Content-Length: 1024
    Content-Range: bytes 0-1023/1073741824

- GET request::

    curl -v https://bwauth.httpd.ip/1G

  It should reply::

    < HTTP/1.1 200 OK
    < Accept-Ranges: bytes
    < Content-Length: 1073741824

- POST request::

    dd if=/dev/zero of=post-20MB.zero bs=1k count=20480
    curl -F "sbwstest=@post-20MB.zero" https://bwauth.httpd.ip/postpath -O
    curl -F "sbwstest=<post-20MB.zero" https://bwauth.httpd.ip/postpath -O

  In the `Xferd` column it should show ``20.0M``::

      % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                Dload  Upload   Total   Spent    Left  Speed
      100 20.0M  100   265  100 20.0M      4   346k  0:01:06  0:00:59  0:00:07    64

If you want, use a `Content delivery network`_ (CDN) in order to make the
destination IP closer to the scanner exit.

scanner setup
----------------------

.. note:: To facilitate debugging, it is recommended that the system timezone
   is set to UTC.

To set the timezone to UTC in Debian::

  apt-get --reinstall install tzdata
  ln -sf /usr/share/zoneinfo/UTC /etc/localtime
  update-initramfs -u

Install sbws according to `<INSTALL.rst>`_ (in the local directory or Tor
Project Gitlab) or `<INSTALL.html>`_  (local build or Read the Docs).

To run the ``scanner`` it is mandatory to create a configuration file with at
least one ``destination``.
It is recommended to set several ``destinations`` so that the ``scanner`` can
continue if one fails.

If ``sbws`` is installed from the Debian package, then create the configuration
file in ``/etc/sbws/sbws.ini``.
You can see an example with all the possible options here, note that you don't
need to include all of that and that everything that starts with ``#`` and
``;`` is a comment:

.. literalinclude:: /examples/sbws.example.ini
    :caption: Example sbws.example.ini

If ``sbws`` is installed from the sources as a non-root user then create the
configuration file in ``~/.sbws.ini``.

More details about the configuration file can be found in
``./docs/source/man_sbws.ini.rst`` (in the local directory or Tor Project
Gitlab) or `<man_sbws.ini.html>`_  (local build or Read the Docs) or
``man sbws.ini`` (system package).

generator setup
---------------

The Debian package also includes a cron job to run the ``generator``.
If sbws is installed in some other way, there should be cron job. For example::

  35 *     * * *   sbws  /usr/local/bin/sbws -c /etc/sbws/sbws.ini generate
  05 0     * * *   sbws  /usr/local/bin/sbws -c /etc/sbws/sbws.ini cleanup

(Note that there is also a command to clean the old data).

If the cron job is configured to send Email alerts on errors, it's probably
better to configure the log level to ``ERROR`` instead of ``WARNING``.

At level ``WARNING``, the first days, the ``generator`` will log every hour
that it hasn't reached enough percentage of relays to report.
After some days, if the scanner is located near fasts exits, it would also log
every hour that it is reporting more than the 50% of the consensus bandwidth.

The log level can be changed in the configuration file, for example::

  to_stdout_level = error

This setup will affect both to the ``generator`` and the ``scanner``, so for
Email alerts, it's probably more convenient to configure it from the command
line, for example::

  /usr/local/bin/sbws --log-level error generate


See also ``./docs/source/man_sbws.rst`` (in the local directory or Tor Project
Gitlab) or `<man_sbws.html>`_ (local build or Read the Docs) or ``man sbws``
(system package).

.. _Content delivery network: https://en.wikipedia.org/wiki/Content_delivery_network

Troubleshooting
---------------

See ``./docs/source/troubleshooting.rst`` (in the local directory or Tor Project
Gitlab) or `<Troubleshooting.html>`_ (local build or Read the Docs)
