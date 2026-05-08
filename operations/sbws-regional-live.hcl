variable "anyone_client_tag" {
  type        = string
  description = "The anyone client container image tag to deploy for the sbws regional live relay task"
}

variable "sbws_tag" {
  type        = string
  description = "The sbws container image tag to deploy for the sbws regional live scanner task"
}

job "sbws-regional-live" {
  datacenters = ["ator-fin"]
  type        = "service"
  namespace   = "live-network"

  update {
    max_parallel      = 2
    healthy_deadline  = "10m"
    progress_deadline = "60m"
  }
  
  constraint {
    attribute = "${meta.pool}"
    value     = "live-network-authorities"
  }
  constraint {
    attribute = "${meta.role}"
    value     = "bandwidth-authority"
  }
  constraint {
    distinct_hosts = true
  }

  group "sbws-us-central-live-group" {
    count = 1

    constraint {
      attribute = "${meta.region}"
      value     = "us-central"
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
      port "http_dest_port" {}
      port "http_file_port" {}
      port "or_port" { static = 9291 }
      port "control_port" { host_network = "wireguard" }
    }

    task "sbws-relay-task" {
      
      lifecycle {
        hook = "prestart"
        sidecar = true
      }
      
      driver = "docker"

      config {
        image = "ghcr.io/anyone-protocol/ator-protocol:${var.anyone_client_tag}"
        image_pull_timeout = "45m"
        volumes = ["local/anonrc:/etc/anon/anonrc"]
      }
      
      consul {}

      volume_mount {
        volume      = "sbws-live"
        destination = "/var/lib/anon"
        read_only   = false
      }

      resources {
        cpu    = 256
        memory = 2048
      }

      template {
        change_mode = "noop"
        data        = <<-EOH
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
        name     = "sbws-relay-standalone-live"
        tags     = ["logging"]
        port     = "or_port"
        check {
          name     = "SBWS standalone live relay or_port alive"
          port     = "or_port"
          type     = "tcp"
          interval = "10s"
          timeout  = "10s"
        }
      }
    }

    task "sbws-destination-task" {
      
      lifecycle {
        hook = "prestart"
        sidecar = true
      }

      driver = "docker"

      config {
        image   = "nginx:1.29"
        volumes = ["local/nginx-sbws:/etc/nginx/conf.d/default.conf:ro"]
        ports = ["http_dest_port"]
      }

      consul {}

      resources {
        cpu    = 128
        memory = 128
      }

      volume_mount {
        volume      = "sbws-destination-live"
        destination = "/data"
        read_only   = false
      }

      template {
        change_mode = "noop"
        data        = <<-EOH
        log_format default '[$time_iso8601] $remote_addr - $remote_user $request $status $body_bytes_sent $http_referer $http_user_agent $http_x_forwarded_for';
        server {
          root /data;
          access_log /dev/stdout default;
          error_log /dev/stderr warn;
          autoindex on;
          listen 0.0.0.0:{{ env `NOMAD_PORT_http_dest_port` }};

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
        name     = "sbws-destination-standalone-live"
        tags     = ["logging"]
        port     = "http_dest_port"
        check {
          name     = "sbws standalone live destination nginx alive"
          type     = "http"
          path     = "/"
          interval = "10s"
          timeout  = "10s"
        }
      }
    }

    task "sbws-scanner-task" {
      driver = "docker"

      config {
        image   = "ghcr.io/anyone-protocol/sbws-scanner:${var.sbws_tag}"
        image_pull_timeout = "45m"
        volumes = [
          "local/.sbws.ini:/root/.sbws.ini:ro"
        ]
      }

      consul {}

      env {
        INTERVAL_MINUTES = "300" # NB: originally 60m, increased to 300m due to netscan rate limiting
      }

      volume_mount {
        volume      = "sbws-live"
        destination = "/root/.sbws"
        read_only   = false
      }

      service {
        name     = "sbws-scanner-standalone-live-task"
        tags     = ["logging"]
      }

      resources {
        cpu    = 256
        memory = 2048
      }

      template {
        change_mode = "noop"
        data        = <<-EOH
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
        url = http://{{ env `NOMAD_HOST_ADDR_http_dest_port` }}/1GiB
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

    task "sbws-fileserver-task" {
      driver = "docker"

      config {
        image   = "nginx:1.29"
        ports   = ["http_file_port"]
        volumes = ["local/nginx.conf:/etc/nginx/nginx.conf:ro"]
      }

      volume_mount {
        volume      = "sbws-live"
        destination = "/source"
        read_only   = true
      }

      template {
        data = <<-EOF
        events {}

        http {
            include       /etc/nginx/mime.types;
            default_type  application/octet-stream;

            # Hardening
            server_tokens off;                 # hide nginx version
            sendfile on;
            tcp_nopush on;
            tcp_nodelay on;

            server {
                listen 0.0.0.0:{{ env `NOMAD_PORT_http_file_port` }};

                # === Simple healthcheck ===
                location = / {
                    access_log off;
                    add_header Content-Type text/plain;
                    return 200 "ok\n";
                }

                # === ONLY allow the exact bandwidth file ===
                location = /latest.v3bw {
                    root /source;
                    try_files $uri =404;       # serve if it exists, else 404

                    # Optional: extra headers for the puller (no caching)
                    expires -1;
                    add_header Cache-Control "no-cache" always;
                    add_header X-Content-Type-Options nosniff;
                }

                # === Deny everything else (including root, other files, etc.) ===
                location / {
                    deny all;
                    # return 404;   # uncomment if you prefer 404 instead of 403 for obscurity
                }
            }
        }
        EOF
        destination = "local/nginx.conf"
      }

      service {
        name = "sbws-bandwidth-us-central"
        port = "http_file_port"
        tags = ["logging"]

        check {
          name     = "sbws standalone live nginx fileserver alive"
          type     = "http"
          path     = "/"
          interval = "10s"
          timeout  = "2s"
        }
      }

      resources {
        cpu    = 128
        memory = 128
      }
    }
  }

  group "sbws-eu-central-live-group" {
    count = 1

    constraint {
      attribute = "${meta.region}"
      value     = "eu-central"
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
      port "http_dest_port" {}
      port "http_file_port" {}
      port "or_port" { static = 9291 }
      port "control_port" { host_network = "wireguard" }
    }

    task "sbws-relay-task" {
      
      lifecycle {
        hook = "prestart"
        sidecar = true
      }
      
      driver = "docker"

      config {
        image = "ghcr.io/anyone-protocol/ator-protocol:${var.anyone_client_tag}"
        image_pull_timeout = "45m"
        volumes = ["local/anonrc:/etc/anon/anonrc"]
      }
      
      consul {}

      volume_mount {
        volume      = "sbws-live"
        destination = "/var/lib/anon"
        read_only   = false
      }

      resources {
        cpu    = 256
        memory = 2048
      }

      template {
        change_mode = "noop"
        data        = <<-EOH
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
        name     = "sbws-relay-standalone-live"
        tags     = ["logging"]
        port     = "or_port"
        check {
          name     = "SBWS standalone live relay or_port alive"
          port     = "or_port"
          type     = "tcp"
          interval = "10s"
          timeout  = "10s"
        }
      }
    }

    task "sbws-destination-task" {
      
      lifecycle {
        hook = "prestart"
        sidecar = true
      }

      driver = "docker"

      config {
        image   = "nginx:1.29"
        volumes = ["local/nginx-sbws:/etc/nginx/conf.d/default.conf:ro"]
        ports = ["http_dest_port"]
      }

      consul {}

      resources {
        cpu    = 128
        memory = 128
      }

      volume_mount {
        volume      = "sbws-destination-live"
        destination = "/data"
        read_only   = false
      }

      template {
        change_mode = "noop"
        data        = <<-EOH
        log_format default '[$time_iso8601] $remote_addr - $remote_user $request $status $body_bytes_sent $http_referer $http_user_agent $http_x_forwarded_for';
        server {
          root /data;
          access_log /dev/stdout default;
          error_log /dev/stderr warn;
          autoindex on;
          listen 0.0.0.0:{{ env `NOMAD_PORT_http_dest_port` }};

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
        name     = "sbws-destination-standalone-live"
        tags     = ["logging"]
        port     = "http_dest_port"
        check {
          name     = "sbws standalone live destination nginx alive"
          type     = "http"
          path     = "/"
          interval = "10s"
          timeout  = "10s"
        }
      }
    }

    task "sbws-scanner-task" {
      driver = "docker"

      config {
        image   = "ghcr.io/anyone-protocol/sbws-scanner:${var.sbws_tag}"
        image_pull_timeout = "45m"
        volumes = [
          "local/.sbws.ini:/root/.sbws.ini:ro"
        ]
      }

      consul {}

      env {
        INTERVAL_MINUTES = "300" # NB: originally 60m, increased to 300m due to netscan rate limiting
      }

      volume_mount {
        volume      = "sbws-live"
        destination = "/root/.sbws"
        read_only   = false
      }

      service {
        name     = "sbws-scanner-standalone-live-task"
        tags     = ["logging"]
      }

      resources {
        cpu    = 256
        memory = 2048
      }

      template {
        change_mode = "noop"
        data        = <<-EOH
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
        url = http://{{ env `NOMAD_HOST_ADDR_http_dest_port` }}/1GiB
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

    task "sbws-fileserver-task" {
      driver = "docker"

      config {
        image   = "nginx:1.29"
        ports   = ["http_file_port"]
        volumes = ["local/nginx.conf:/etc/nginx/nginx.conf:ro"]
      }

      volume_mount {
        volume      = "sbws-live"
        destination = "/source"
        read_only   = true
      }

      template {
        data = <<-EOF
        events {}

        http {
            include       /etc/nginx/mime.types;
            default_type  application/octet-stream;

            # Hardening
            server_tokens off;                 # hide nginx version
            sendfile on;
            tcp_nopush on;
            tcp_nodelay on;

            server {
                listen 0.0.0.0:{{ env `NOMAD_PORT_http_file_port` }};

                # === Simple healthcheck ===
                location = / {
                    access_log off;
                    add_header Content-Type text/plain;
                    return 200 "ok\n";
                }

                # === ONLY allow the exact bandwidth file ===
                location = /latest.v3bw {
                    root /source;
                    try_files $uri =404;       # serve if it exists, else 404

                    # Optional: extra headers for the puller (no caching)
                    expires -1;
                    add_header Cache-Control "no-cache" always;
                    add_header X-Content-Type-Options nosniff;
                }

                # === Deny everything else (including root, other files, etc.) ===
                location / {
                    deny all;
                    # return 404;   # uncomment if you prefer 404 instead of 403 for obscurity
                }
            }
        }
        EOF
        destination = "local/nginx.conf"
      }

      service {
        name = "sbws-bandwidth-eu-central"
        port = "http_file_port"
        tags = ["logging"]

        check {
          name     = "sbws standalone live nginx fileserver alive"
          type     = "http"
          path     = "/"
          interval = "10s"
          timeout  = "2s"
        }
      }

      resources {
        cpu    = 128
        memory = 128
      }
    }
  }
}
