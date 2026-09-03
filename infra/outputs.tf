output "image_repository" {
  description = "Tag your agent image with this, then re-apply with -var image=<tag>."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.agent.repository_id}"
}

output "proxy_command" {
  description = "Run this, then open http://localhost:8080. It is how everyone reaches the agent."
  value       = "gcloud run services proxy ${google_cloud_run_v2_service.agent.name} --region ${var.region} --project ${var.project_id}"
}

output "service_account" {
  description = "The identity the agent runs as."
  value       = google_service_account.agent.email
}

output "bucket" {
  description = "Where analysed documents are archived."
  value       = google_storage_bucket.archive.name
}

output "firestore_database" {
  description = "Named database. The persistence tool must pass it explicitly; the client defaults to (default), which this stack does not create."
  value       = google_firestore_database.invoices.name
}
