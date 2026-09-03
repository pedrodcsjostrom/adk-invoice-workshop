# The one deployable: the ADK developer UI, plus the records page it serves
# from its own identity.
#
# The service is private. There is no allUsers invoker binding and no
# invoker-iam-disabled annotation, because domain restricted sharing blocks the
# first for corporate attendees and the second removes authentication from a UI
# that can read everything. Everyone reaches it the same way:
#   gcloud run services proxy <name> --region <region> --project <project>
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
