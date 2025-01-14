job "sbws-live" {
  datacenters = ["ator-fin"]
  type        = "service"
  namespace   = "ator-network"

  update {
    max_parallel      = 1
    healthy_deadline  = "15m"
    progress_deadline = "20m"
  }

  group "sbws-live-group" {
    count = 7

    spread {
      attribute = "${node.unique.id}"
      weight    = 100
      target "067a42a8-d8fe-8b19-5851-43079e0eabb4" {
        percent = 14
      }
      target "16be0723-edc1-83c4-6c02-193d96ec308a" {
        percent = 14
      }
      target "e6e0baed-8402-fd5c-7a15-8dd49e7b60d9" {
        percent = 14
      }
      target "5ace4a92-63c4-ac72-3ed1-e4485fa0d4a4" {
        percent = 14
      }
      target "eb42c498-e7a8-415f-14e9-31e9e71e5707" {
        percent = 14
      }
      target "4aa61f61-893a-baf4-541b-870e99ac4839" {
        percent = 15
      }
      target "c2adc610-6316-cd9d-c678-cda4b0080b52" {
        percent = 15
      }
    }

    volume "sbws-live" {
      type      = "host"
      read_only = false
      source    = "sbws-live"
    }

    volume "sbws-destination-live" {
      type      = "host"
      read_only = true
      source    = "sbws-destination-live"
    }

    network {
      mode = "bridge"

      port "http-port" {
        static = 9277
      }

      port "orport" {
        static = 9291
      }

      port "control-port" {
        static = 9251
        host_network = "wireguard"
      }
    }

    task "sbws-relay-live-task" {
      driver = "docker"

      volume_mount {
        volume      = "sbws-live"
        destination = "/var/lib/anon"
        read_only   = false
      }

      config {
        image      = "ghcr.io/anyone-protocol/ator-protocol:d903d014fe7d77a113791e27629e6f22380d9e57" // v0.4.9.10
        image_pull_timeout = "15m"
        volumes    = [
          "local/anonrc:/etc/anon/anonrc"
        ]
      }

      resources {
        cpu    = 2048
        memory = 2500
      }

      template {
        change_mode = "noop"
        data        = <<EOH
User anond

Nickname AnonSBWS

DataDirectory /var/lib/anon/anon-data

ControlPort {{ env `NOMAD_PORT_control_port` }}

SocksPort auto

ConnectionPadding auto
SafeLogging 0
UseEntryGuards 0
ProtocolWarnings 1
FetchDirInfoEarly 1
LogTimeGranularity 1
UseMicrodescriptors 0
FetchDirInfoExtraEarly 1
FetchUselessDescriptors 1
LearnCircuitBuildTimeout 0

AgreeToTerms 1

ORPort {{ env `NOMAD_PORT_orport` }}
        EOH
        destination = "local/anonrc"
      }

      service {
        name     = "sbws-relay-live"
        tags     = ["logging"]
        port     = "control-port"
      }
    }

    task "sbws-scanner-live-task" {
      driver = "docker"

      env {
        INTERVAL_MINUTES = "60"
      }

      volume_mount {
        volume      = "sbws-live"
        destination = "/root/.sbws"
        read_only   = false
      }

      config {
        image   = "ghcr.io/anyone-protocol/sbws-scanner:DEPLOY_TAG"
        image_pull_timeout = "15m"
        volumes = [
          "local/.sbws.ini:/root/.sbws.ini:ro"
        ]
      }

      service {
        name     = "sbws-scanner-live-task"
        tags     = ["logging"]
      }

      resources {
        cpu    = 1024
        memory = 3072
      }

      template {
        change_mode = "noop"
        data        = <<EOH
# Minimum configuration that needs to be customized
[scanner]
# ISO 3166-1 alpha-2 country code where the scanner is located.
# Default AA, to detect it was not edited.
country = ZZ
# A human-readable string with chars in a-zA-Z0-9 to identify the dirauth
# nickname that will publish the BandwidthFiles generated from this scanner.
# Default to a non existing dirauth_nickname to detect it was not edited.
dirauth_nickname = Anon

[destinations]
# A destination can be disabled changing `on` by `off`
dest = on

[destinations.dest]
# the domain and path to the 1GB file.
url = http://{{ env `NOMAD_HOST_ADDR_http-port` }}/1GiB
# Whether to verify or not the TLS certificate. Default True.
verify = False
# ISO 3166-1 alpha-2 country code where the Web server destination is located.
# Default AA, to detect it was not edited.
# Use ZZ if the location is unknown (for instance, a CDN).
country = ZZ

[tor]
datadir = /root/.sbws/anon-data
external_control_ip = {{ env `NOMAD_IP_control_port` }}
external_control_port = {{ env `NOMAD_PORT_control_port` }}
        EOH
        destination = "local/.sbws.ini"
      }

    }

    task "sbws-destination-live-task" {
      driver = "docker"

      config {
        image   = "nginx:1.27"
        volumes = [
          "local/nginx-sbws:/etc/nginx/conf.d/default.conf:ro"
        ]
        ports = ["http-port"]
      }

      resources {
        cpu    = 128
        memory = 2048
      }

      volume_mount {
        volume      = "sbws-destination-live"
        destination = "/data"
        read_only   = false
      }

      service {
        name     = "sbws-destination-live"
        tags     = ["logging"]
        port     = "http-port"
        check {
          name     = "sbws live destination nginx alive"
          type     = "http"
          path     = "/"
          interval = "10s"
          timeout  = "10s"
          check_restart {
            limit = 3
            grace = "10s"
          }
        }
      }

      template {
        change_mode = "noop"
        data        = <<EOH
    log_format default '[$time_iso8601] $remote_addr - $remote_user $request $status $body_bytes_sent $http_referer $http_user_agent $http_x_forwarded_for';
    server {
      root /data;
      access_log /dev/stdout default;
      error_log /dev/stderr warn;
      autoindex on;
      listen 0.0.0.0:{{ env `NOMAD_PORT_http_port` }};

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
