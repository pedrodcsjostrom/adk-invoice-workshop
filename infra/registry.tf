# The repository the agent image is pushed to. It exists after the first
# apply, which is what makes the build-and-push step possible at all.
resource "google_artifact_registry_repository" "agent" {
  repository_id = var.name
  location      = var.region
  format        = "DOCKER"
  description   = "Container images for the invoice-analyzer agent"
}
