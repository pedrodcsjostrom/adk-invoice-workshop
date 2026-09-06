# The one deployable: our own FastAPI application, serving the upload page and
# the records page from its own identity. The ADK developer UI is not deployed
# and stays a local tool under `adk web` (ADR-0001).
#
# The service is private. There is no allUsers invoker binding and no
# invoker-iam-disabled annotation, because domain restricted sharing blocks the
# first for corporate attendees and the second removes authentication from
# pages that can read every record filed. Everyone reaches it the same way, one
# command, which runs the proxy and deletes the Origin header Cloud Run refuses
# on an upload from a browser (ADR-0004):
#   python scripts/origin_shim.py --project <project>
resource "google_cloud_run_v2_service" "agent" {
  name     = var.name
  location = var.region

  # Explicit, so nothing depends on the deploy-time default.
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.agent.email

    scaling {
      # The single largest lever on idle cost: an always-warm instance costs
      # roughly 86 times more than a scale-to-zero one over a quiet week.
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = var.image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      env {
        name  = "GOOGLE_GENAI_USE_ENTERPRISE"
        value = "TRUE"
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }

      # The model endpoint, not the infrastructure region.
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.model_location
      }

      env {
        name  = "INVOICE_MODEL"
        value = var.model
      }

      env {
        name  = "INVOICE_BUCKET"
        value = google_storage_bucket.archive.name
      }

      env {
        name  = "FIRESTORE_DATABASE"
        value = google_firestore_database.invoices.name
      }
    }
  }

  depends_on = [
    google_artifact_registry_repository_iam_member.agent_pull,
  ]
}
