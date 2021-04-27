.. simple-bw-scanner documentation master file, created by
   sphinx-quickstart on Fri Mar 23 16:20:02 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. raw:: html

  <script type="text/javascript">
  if (String(window.location).indexOf("readthedocs") !== -1) {
    window.alert('The documentation has moved, redirecting...');
    window.location.replace('https://tpo.pages.torproject.net/network-health/sbws');
  }
  </script>
  <noscript>
    NOTE: documentation has moved from https://sbws.readthedocs.org to
    https://tpo.pages.torproject.net/network-health/sbws
  </noscript>

Welcome to Simple Bandwidth Scanner's documentation!
====================================================

User main documentation
------------------------

Included in the
`repository root <https://gitweb.torproject.org/sbws.git//tree/>`_
and in ``sbws`` Debian package:

.. toctree::
   :maxdepth: 1

   README
   INSTALL
   DEPLOY
   CHANGELOG
   AUTHORS
   man_sbws
   man_sbws.ini

.. _dev_doc:

Developer/technical documentation
----------------------------------

Included in the
`docs directory <https://gitweb.torproject.org/sbws.git/tree/docs>`_ and in
``sbws-doc`` Debian package:

.. toctree::
   :maxdepth: 1

   contributing
   testing
   documenting
   how_works
   generator
   torflow_aggr
   differences
   code_design
   state
   config
   config_tor
   sbws
   implementation
   bandwidth_distribution
   tor_bandwidth_files
   bandwidth_authorities
   monitoring_bandwidth
   roadmap
   glossary
   faq

Proposals:

.. toctree::
   :maxdepth: 1
   :glob:

   proposals/*

Indices and tables
-------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
