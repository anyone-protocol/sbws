job "sbws-stage" {
  datacenters = ["ator-fin"]
  type        = "service"
  namespace   = "ator-network"

  group "sbws-stage-group" {
    count = 1

    #    volume "sbws-data" {
    #       type      = "host"
    #       read_only = false
    #       source    = "sbws-stage"
    #    }

    network {
      #      mode = "bridge"
      port "http-port" {
        static = 9888
        to     = 80
        #        host_network = "wireguard"
      }
    }

    ephemeral_disk {
      migrate = true
      sticky  = true
    }

    task "sbws-scanner-stage-task" {
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
        image   = "svforte/sbws-scanner:latest"
        force_pull = true
        volumes = [
          "local/.sbws.ini:/root/.sbws.ini:ro",
          "local/anonrc:/etc/anon/anonrc:ro",
          "local/data:/root/.sbws"
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
# A destination can be disabled changing `on` by `off`
dest = on

[destinations.dest]
# the domain and path to the 1GB file.
url = http://host.docker.internal:8888/1GiB
# Whether to verify or not the TLS certificate. Default True.
verify = False
# ISO 3166-1 alpha-2 country code where the Web server destination is located.
# Default AA, to detect it was not edited.
# Use ZZ if the location is unknown (for instance, a CDN).
country = ZZ

[tor]
control_socket = /var/lib/anon/control
        EOH
        destination = "local/.sbws.ini"
      }

      template {
        change_mode = "noop"
        data        = <<EOH
User debian-anon
DataDirectory /var/lib/anon
ControlSocket /var/lib/anon/control
Nickname AnonSBWS
FetchUselessDescriptors 1
        EOH
        destination = "local/anonrc"
      }
    }

    task "sbws-destination-stage-task" {
      driver = "docker"

      #      volume_mount {
      #        volume      = "sbws-data"
      #        destination = "/var/www/sbws-destination/data"
      #        read_only   = true
      #      }

      config {
        image   = "svforte/sbws-destination:latest"
        force_pull = true
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
        name     = "sbws-destination-stage"
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
