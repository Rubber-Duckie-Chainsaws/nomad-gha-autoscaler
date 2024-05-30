job "gha-autoscheduler" {
  datacenters = ["aws-NYC-1"]
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
        memory = 128
      }

      config {
        image = "434190342226.dkr.ecr.us-east-1.amazonaws.com/nomad/gha-autoscaler:latest"

        ports = ["web"]
      }

      vault {}

      template {
        data = "GITHUB_SECRET={{ with secret \"kv/data/default/gha-autoscheduler/config\" }}{{.Data.data.secret}}{{ end }}"
        destination = "secrets/env"
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
}
