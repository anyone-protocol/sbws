job "sbws-stage" {
  datacenters = ["ator-fin"]
  type        = "service"
  namespace   = "ator-network"

  spread {
    attribute = "${node.unique.id}"
    weight    = 100
    target "f3f664d6-7d65-be58-4a2c-4c66e20f1a9f" {
      percent = 43
    }
    target "232ea736-591c-4753-9dcc-3e815c4326af" {
      percent = 43
    }
    target "4ca2fc3c-8960-6ae7-d931-c0d6030d506b" {
      percent = 14
    }
  }

  group "sbws-stage-group" {
    count = 3

    constraint {
      attribute = "${node.unique.id}"
      operator  = "set_contains_any"
      value     = "4ca2fc3c-8960-6ae7-d931-c0d6030d506b,232ea736-591c-4753-9dcc-3e815c4326af,f3f664d6-7d65-be58-4a2c-4c66e20f1a9f"
    }

    constraint {
      operator = "distinct_hosts"
      value    = "true"
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
      }

      port "orport" {
        static = 19101
      }

      port "control-port" {
        static = 19151
        host_network = "wireguard"
      }
    }

    task "sbws-relay-stage-task" {
      driver = "docker"

      volume_mount {
        volume      = "sbws-stage"
        destination = "/var/lib/anon"
        read_only   = false
      }

      config {
        image      = "ghcr.io/anyone-protocol/ator-protocol-stage:latest"
        volumes    = [
          "local/anonrc:/etc/anon/anonrc"
        ]
      }

      resources {
        cpu    = 2048
        memory = 2560
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
        name     = "sbws-relay-stage"
        tags     = ["logging"]
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
        image   = "ghcr.io/anyone-protocol/sbws-scanner:DEPLOY_TAG"
        volumes = [
          "local/.sbws.ini:/root/.sbws.ini:ro"
        ]
      }

      service {
        name     = "sbws-scanner-stage-task"
        tags     = ["logging"]
      }

      resources {
        cpu    = 1024
        memory = 2560
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
        memory = 256
      }

      volume_mount {
        volume      = "sbws-destination-stage"
        destination = "/data"
        read_only   = true
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

  group "sbws-stage-group-2" {
    count = 2

    constraint {
      attribute = "${node.unique.id}"
      operator  = "set_contains_any"
      value     = "232ea736-591c-4753-9dcc-3e815c4326af,f3f664d6-7d65-be58-4a2c-4c66e20f1a9f"
    }

    constraint {
      operator = "distinct_hosts"
      value    = "true"
    }

    volume "sbws-stage-2" {
      type      = "host"
      read_only = false
      source    = "sbws-stage-2"
    }

    volume "sbws-destination-stage-2" {
      type      = "host"
      read_only = true
      source    = "sbws-destination-stage-2"
    }

    network {
      mode = "bridge"

      port "http-port" {
        static = 9178
      }

      port "orport" {
        static = 19102
      }

      port "control-port" {
        static = 19152
        host_network = "wireguard"
      }
    }

    task "sbws-relay-stage-task" {
      driver = "docker"

      volume_mount {
        volume      = "sbws-stage-2"
        destination = "/var/lib/anon"
        read_only   = false
      }

      config {
        image      = "ghcr.io/anyone-protocol/ator-protocol-stage:latest"
        volumes    = [
          "local/anonrc:/etc/anon/anonrc"
        ]
      }

      resources {
        cpu    = 2048
        memory = 2560
      }

      template {
        change_mode = "noop"
        data        = <<EOH
User anond

Nickname AnonSBWS

DataDirectory /var/lib/anon/anon-data
AgreeToTerms 1

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

ORPort {{ env `NOMAD_PORT_orport` }}
        EOH
        destination = "local/anonrc"
      }

      service {
        name     = "sbws-relay-stage-2"
        tags     = ["logging"]
        port     = "control-port"
      }
    }

    task "sbws-scanner-stage-task" {
      driver = "docker"

      env {
        INTERVAL_MINUTES = "60"
      }

      volume_mount {
        volume      = "sbws-stage-2"
        destination = "/root/.sbws"
        read_only   = false
      }

      config {
        image   = "ghcr.io/anyone-protocol/sbws-scanner:DEPLOY_TAG"
        volumes = [
          "local/.sbws.ini:/root/.sbws.ini:ro"
        ]
      }

      service {
        name     = "sbws-scanner-stage-task-2"
        tags     = ["logging"]
      }

      resources {
        cpu    = 1024
        memory = 2560
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
        memory = 256
      }

      volume_mount {
        volume      = "sbws-destination-stage-2"
        destination = "/data"
        read_only   = true
      }

      service {
        name     = "sbws-destination-stage-2"
        tags     = ["logging"]
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

  group "sbws-stage-group-3" {
    count = 2

     constraint {
      attribute = "${node.unique.id}"
      operator  = "set_contains_any"
      value     = "232ea736-591c-4753-9dcc-3e815c4326af,f3f664d6-7d65-be58-4a2c-4c66e20f1a9f"
    }
    
    constraint {
      operator = "distinct_hosts"
      value    = "true"
    }

    volume "sbws-stage-3" {
      type      = "host"
      read_only = false
      source    = "sbws-stage-3"
    }

    volume "sbws-destination-stage-3" {
      type      = "host"
      read_only = true
      source    = "sbws-destination-stage-3"
    }

    network {
      mode = "bridge"

      port "http-port" {
        static = 9179
      }

      port "orport" {
        static = 19103
      }

      port "control-port" {
        static = 19153
        host_network = "wireguard"
      }
    }

    task "sbws-relay-stage-task" {
      driver = "docker"

      volume_mount {
        volume      = "sbws-stage-3"
        destination = "/var/lib/anon"
        read_only   = false
      }

      config {
        image      = "ghcr.io/anyone-protocol/ator-protocol-stage:latest"
        volumes    = [
          "local/anonrc:/etc/anon/anonrc"
        ]
      }

      resources {
        cpu    = 2048
        memory = 2560
      }

      template {
        change_mode = "noop"
        data        = <<EOH
User anond

Nickname AnonSBWS

DataDirectory /var/lib/anon/anon-data
AgreeToTerms 1

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

ORPort {{ env `NOMAD_PORT_orport` }}
        EOH
        destination = "local/anonrc"
      }

      service {
        name     = "sbws-relay-stage-3"
        tags     = ["logging"]
        port     = "control-port"
      }
    }

    task "sbws-scanner-stage-task" {
      driver = "docker"

      env {
        INTERVAL_MINUTES = "60"
      }

      volume_mount {
        volume      = "sbws-stage-3"
        destination = "/root/.sbws"
        read_only   = false
      }

      config {
        image   = "ghcr.io/anyone-protocol/sbws-scanner:DEPLOY_TAG"
        volumes = [
          "local/.sbws.ini:/root/.sbws.ini:ro"
        ]
      }

      service {
        name     = "sbws-scanner-stage-task-3"
        tags     = ["logging"]
      }

      resources {
        cpu    = 1024
        memory = 2560
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
        memory = 256
      }

      volume_mount {
        volume      = "sbws-destination-stage-3"
        destination = "/data"
        read_only   = true
      }

      service {
        name     = "sbws-destination-stage-3"
        tags     = ["logging"]
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
