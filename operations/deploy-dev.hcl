job "sbws-dev" {
  datacenters = ["ator-fin"]
  type        = "service"
  namespace   = "ator-network"

  group "sbws-dev-group" {
    count = 1

#    volume "sbws-data" {
#       type      = "host"
#       read_only = false
#       source    = "sbws-dev"
#    }

    network {
#      mode = "bridge"
      port "http-port" {
        static = 9000
        to     = 80
#        host_network = "wireguard"
      }
    }

    ephemeral_disk {
      migrate = true
      sticky  = true
    }

    task "sbws-scanner-dev-task" {
      driver = "docker"

#      env {
#        LOGBASE = "data/logs"
#      }

#      volume_mount {
#         volume      = "sbws-data"
#         destination = "/srv/sbws/data"
#         read_only   = false
#      }

      config {
        image   = "svforte/sbws-scanner:latest-dev"
        volumes = [
          "local/.sbws.ini:/root/.sbws.ini:ro",
          "local/data:/app/scanner/data"
        ]
      }

      resources {
        cpu    = 256
        memory = 1024
      }

      template {
        change_mode = "noop"
        data        = <<EOH
# Minimum configuration that needs to be customized
[scanner]
# ISO 3166-1 alpha-2 country code where the scanner is located.
# Default AA, to detect it was not edited.
country = DE
# A human-readable string with chars in a-zA-Z0-9 to identify the dirauth
# nickname that will publish the BandwidthFiles generated from this scanner.
# Default to a non existing dirauth_nickname to detect it was not edited.
dirauth_nickname = Anon

[destinations]
# With several destinations, the scanner can continue even if some of them
# fail, which can be caused by a network problem on their side.
# If all of them fail, the scanner will stop, which
# will happen if there is network problem on the scanner side.

# A destination can be disabled changing `on` by `off`
foo = on

[destinations.foo]
# the domain and path to the 1GB file or POST URL.
url = http://host.docker.internal:8888/1GiB
# Whether to verify or not the TLS certificate. Default True
verify = False
# ISO 3166-1 alpha-2 country code where the Web server destination is located.
# Default AA, to detect it was not edited.
# Use ZZ if the location is unknown (for instance, a CDN).
country = ZZ

## The following logging options are set by default.
## There is no need to change them unless other options are preferred.
; [logging]
; # Whether or not to log to a rotating file the directory paths.log_dname
; to_file = yes
; # Whether or not to log to stdout
; to_stdout = yes
; # Whether or not to log to syslog
; # NOTE that when sbws is launched by systemd, stdout goes to journal and
; # syslog.
; to_syslog = no

; # Level to log at. Debug, info, warning, error, critical.
; # `level` must be set to the lower of all the handler levels.
; level = debug
; to_file_level = debug
; to_stdout_level = info
; to_syslog_level = info
; # Format string to use when logging
; format = %(module)s[%(process)s]: <%(levelname)s> %(message)s
; # verbose formatter useful for debugging
; to_file_format = %(asctime)s %(levelname)s %(threadName)s %(filename)s:%(lineno)s - %(funcName)s - %(message)s
; # Not adding %(asctime)s to to stdout since it'll go to syslog when using
; # systemd, and it'll have already the date.
; to_stdout_format = ${format}
; to_syslog_format = ${format}

# To disable certificate validation, uncomment the following
# verify = False
        EOH
        destination = "local/.sbws.ini"
      }
    }

    task "sbws-destination-dev-task" {
      driver = "docker"

#      volume_mount {
#        volume      = "sbws-data"
#        destination = "/var/www/sbws-destination/data"
#        read_only   = true
#      }

      config {
        image   = "svforte/sbws-destination:latest-dev"
        volumes = [
          "local/nginx-sbws:/etc/nginx/conf.d/default.conf:ro"
        ]
        ports = ["http-port"]
      }

      resources {
        cpu    = 256
        memory = 256
      }

      service {
        name     = "sbws-destination-dev"
        provider = "nomad"
        tags     = ["sbws"]
        port     = "http-port"
        check {
          name     = "sbws destination nginx http server alive"
          type     = "tcp"
          interval = "10s"
          timeout  = "10s"
          check_restart {
            limit = 10
            grace = "30s"
          }
        }
      }

      template {
        change_mode = "noop"
        data        = <<EOH
server {
  root /app/destination/data;

  autoindex on;

  listen 0.0.0.0:80;

  location / {
    try_files $uri $uri/ =404;
  }

  location ~/\.ht {
    deny all;
  }
}
        EOH
        destination = "local/nginx-sbws"
      }
    }
  }
}
