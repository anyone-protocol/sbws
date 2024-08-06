job "sbws-stage" {
  datacenters = ["ator-fin"]
  type        = "service"
  namespace   = "ator-network"

  group "sbws-stage-group" {
    count = 3

    update {
      max_parallel      = 1
      health_check      = "task_states"
      min_healthy_time  = "60m"
      healthy_deadline  = "64m"
      progress_deadline = "70m"
      auto_revert       = true
      auto_promote      = false
      canary            = 0
    }

    spread {
      attribute = "${node.unique.id}"
      weight    = 100
      target "c8e55509-a756-0aa7-563b-9665aa4915ab" {
        percent = 34
      }
      target "c2adc610-6316-cd9d-c678-cda4b0080b52" {
        percent = 33
      }
      target "4aa61f61-893a-baf4-541b-870e99ac4839" {
        percent = 33
      }
    }

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

      port "http-port" {
        static = 9177
        to     = 80
        #        host_network = "wireguard"
      }

      port "control-port" {
        static = 9151
        host_network = "wireguard"
      }

      port "orport" {
        static = 9191
      }
    }

    task "sbws-relay-stage-task" {
      driver = "docker"

      env {
        ANON_USER = "root"
      }

      volume_mount {
        volume      = "sbws-stage"
        destination = "/var/lib/anon"
        read_only   = false
      }

      config {
        image      = "svforte/anon-stage"
        force_pull = true
        volumes    = [
          "local/anonrc:/etc/anon/anonrc"
        ]
      }

      resources {
        cpu    = 256
        memory = 2500
      }

      template {
        change_mode = "noop"
        data        = <<EOH
User root

Nickname AnonSBWS

DataDirectory /var/lib/anon/anon-data

ControlPort {{ env `NOMAD_PORT_control_port` }}

SocksPort auto
SafeLogging 1
UseEntryGuards 0
ProtocolWarnings 1
FetchDirInfoEarly 1
LogTimeGranularity 1
UseMicrodescriptors 0
FetchDirInfoExtraEarly 1
FetchUselessDescriptors 1
LearnCircuitBuildTimeout 0

ORPort {{ env `NOMAD_PORT_orport` }}
        EOH
        destination = "local/anonrc"
      }

      service {
        name     = "sbws-relay-stage"
        tags     = ["sbws", "logging"]
        port     = "control-port"
      }
    }

    task "sbws-scanner-stage-task" {
      driver = "docker"

      env {
        INTERVAL_MINUTES = "60"
      }

      volume_mount {
        volume      = "sbws-stage"
        destination = "/root/.sbws"
        read_only   = false
      }

      config {
        image   = "svforte/sbws-scanner:latest-stage"
        force_pull = true
        volumes = [
          "local/.sbws.ini:/root/.sbws.ini:ro"
        ]
      }

      service {
        name     = "sbws-scanner-stage-task"
        tags     = ["logging"]
      }

      resources {
        cpu    = 1000
        memory = 2500
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


    task "sbws-destination-stage-task" {
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
        memory = 1500
      }

      volume_mount {
        volume      = "sbws-destination-stage"
        destination = "/data"
        read_only   = false
      }

      service {
        name     = "sbws-destination-stage"
        tags     = ["sbws", "logging"]
        port     = "http-port"
        check {
          name     = "sbws stage destination nginx alive"
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
    server {
      root /data;

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
