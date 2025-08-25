job "sbws-stage" {
  datacenters = ["ator-fin"]
  type        = "service"
  namespace   = "stage-network"

  update {
    max_parallel      = 1
    healthy_deadline  = "15m"
    progress_deadline = "20m"
  }
  
  constraint {
    attribute = "${meta.pool}"
    value = "stage-network-authorities"
  }
  constraint {
    distinct_hosts = true
  }

  group "sbws-stage-group" {
    count = 3

    volume "sbws-stage" {
      type      = "host"
      read_only = false
      source    = "sbws-stage"
    }

    volume "sbws-destination-stage" {
      type      = "host"
      read_only = true
      source    = "sbws-destination-stage"
    }

    network {
      mode = "bridge"

      port "http-port" {}

      port "or-port" {
        static = 9191
      }

      port "control-port" {
        host_network = "wireguard"
      }
    }

    task "sbws-relay-stage-task" {
      
      lifecycle {
        hook = "prestart"
        sidecar = true
      }
      
      driver = "docker"

      config {
        image      = "ghcr.io/anyone-protocol/ator-protocol:bd506a47f917355bbe2742418481ec53bb89b261" // v0.4.9.11
        image_pull_timeout = "45m"
        volumes    = [
          "local/anonrc:/etc/anon/anonrc"
        ]
      }
      
      consul {}

      volume_mount {
        volume      = "sbws-stage"
        destination = "/var/lib/anon"
        read_only   = false
      }

      resources {
        cpu    = 512
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

ORPort {{ env `NOMAD_PORT_or_port` }}
        EOH
        destination = "local/anonrc"
      }

      service {
        name     = "sbws-relay-stage"
        tags     = ["logging"]
        port     = "control-port"
        check {
          name     = "SBWS stage relay or-port alive"
          port     = "or-port"
          type     = "tcp"
          interval = "10s"
          timeout  = "10s"
        }
        check {
          name     = "SBWS stage relay control-port alive"
          port     = "control-port"
          type     = "tcp"
          interval = "10s"
          timeout  = "10s"
        }
      }
    }

    task "sbws-destination-stage-task" {
      
      lifecycle {
        hook = "prestart"
        sidecar = true
      }

      driver = "docker"

      config {
        image   = "nginx:1.29"
        volumes = [
          "local/nginx-sbws:/etc/nginx/conf.d/default.conf:ro"
        ]
        ports = ["http-port"]
      }

      consul {}

      resources {
        cpu    = 128
        memory = 256
      }

      volume_mount {
        volume      = "sbws-destination-stage"
        destination = "/data"
        read_only   = false
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

      service {
        name     = "sbws-destination-stage"
        tags     = ["logging"]
        port     = "http-port"
        check {
          name     = "sbws stage destination nginx alive"
          type     = "http"
          path     = "/"
          interval = "10s"
          timeout  = "10s"
        }
      }
    }

    task "sbws-scanner-stage-task" {
      driver = "docker"

      config {
        image   = "ghcr.io/anyone-protocol/sbws-scanner:DEPLOY_TAG"
        image_pull_timeout = "45m"
        volumes = [
          "local/.sbws.ini:/root/.sbws.ini:ro"
        ]
      }

      consul {}

      env {
        INTERVAL_MINUTES = "60"
      }

      volume_mount {
        volume      = "sbws-stage"
        destination = "/root/.sbws"
        read_only   = false
      }

      service {
        name     = "sbws-scanner-stage-task"
        tags     = ["logging"]
      }

      resources {
        cpu    = 512
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
  }
}
