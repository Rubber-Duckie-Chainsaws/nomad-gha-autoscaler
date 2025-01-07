job "gha-autoscheduler" {
  datacenters = ["aws-NYC-1"]
  namespace = "build"
  type = "service"

  constraint {
    attribute = "${node.class}"
    value = "worker"
  }


  group "webhook" {
    count = 1

    network {
      port "web" {
        to = 5000
      }
    }

    task "flask-server" {
      driver = "docker"

      resources {
        cpu = 70
        memory = 72
      }

      config {
        image = "434190342226.dkr.ecr.us-east-1.amazonaws.com/gha-autoscaler/webhook:v2"

        ports = ["web"]
      }

      vault {}

      identity {
        env = true
      }

      template {
        data = <<EOH
{{ with secret "kv/data/build/gha-autoscheduler/config" }}
GITHUB_SECRET={{.Data.data.secret}}
RABBIT_USER={{.Data.data.admin_user}}
RABBIT_PASS="{{.Data.data.admin_pass}}"
{{ end }}
RABBIT_URL="rabbit.service.consul:{{ range service "rabbit" }}{{ .Port }}{{ end }}"
RABBIT_VHOST="/"
EOH
        destination = "secrets/env"
        env         = true
      }

      service {
        name = "gha-webhook"
        provider = "consul"
        tags = [
          "traefik.enable=true",
          "traefik.http.routers.gha-webhook-https.tls=true",
          "traefik.http.routers.gha-webhook-https.entrypoints=websecure",
          "traefik.http.routers.gha-webhook-https.tls.certresolver=myresolver",
          "traefik.http.routers.gha-webhook-https.tls.domains[0].main=gha.tipene.dev",
          "traefik.http.routers.gha-webhook-https.rule=Host(`gha.tipene.dev`)",
        ]
        port = "web"
      }
    }
  }

  group "worker" {
    task "celery" {
      driver = "docker"
      kill_signal = "SIGTERM"
      kill_timeout = "20s"

      restart {
        attempts = "3"
        interval = "10m"
        delay    = "15s"
        mode     = "delay"
      }

      resources {
        cpu = 90
        memory = 140
      }

      template {
        data = <<EOH
{{ with secret "kv/data/build/gha-autoscheduler/gha" }}
{{.Data.data.priv}}
{{ end }}
EOH

        destination = "secrets/pki"
      }

      template {
        data = <<EOH
CONSUL_ADDR          = "{{ env "attr.unique.network.ip-address" }}"
{{ with secret "kv/data/build/gha-autoscheduler/gha" }}
GH_APP_CLIENT_ID     = "{{.Data.data.client_id}}"
GH_APP_INSTALL_ID    = "{{.Data.data.install_id}}"
{{ end }}
{{ with secret "kv/data/build/gha-autoscheduler/config" }}
RABBIT_USER          = "{{.Data.data.admin_user}}"
RABBIT_PASS          = "{{.Data.data.admin_pass}}"
{{ end }}
RABBIT_URL           = "rabbit.service.consul:{{ range service "rabbit" }}{{ .Port }}{{ end }}"
RABBIT_VHOST         = "/"
EOH
        destination = "secrets/env"
        env         = true
      }

      vault {}

      identity {
        env = true
      }

      config {
        image = "434190342226.dkr.ecr.us-east-1.amazonaws.com/gha-autoscaler/worker:v2"

        force_pull = true

        volumes = [
          "secrets/pki:/etc/pki"
        ]
      }
    }
  }
}
