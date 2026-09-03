# A service account this stack owns, rather than the Compute Engine default.
# The default account only exists once the Compute Engine API is on, and
# whether it carries Editor depends on an organization policy that flipped in
# May 2024. Owning the identity removes that variance from the room.
resource "google_service_account" "agent" {
  account_id   = var.name
  display_name = "Invoice analyzer agent runtime"
}

# Calls Gemini through application default credentials. Displayed in the
# console as "Gemini Enterprise Agent Platform User".
resource "google_project_iam_member" "agent_vertex" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = google_service_account.agent.member
}

# Reads and writes invoice records. Firestore has no per-database IAM, so this
# is necessarily project-wide.
resource "google_project_iam_member" "agent_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = google_service_account.agent.member
}

# Objects only. storage.admin would hand the runtime control of the bucket.
resource "google_storage_bucket_iam_member" "agent_archive" {
  bucket = google_storage_bucket.archive.name
  role   = "roles/storage.objectUser"
  member = google_service_account.agent.member
}

# Pulls its own image at deploy time.
resource "google_artifact_registry_repository_iam_member" "agent_pull" {
  project    = var.project_id
  location   = google_artifact_registry_repository.agent.location
  repository = google_artifact_registry_repository.agent.name
  role       = "roles/artifactregistry.reader"
  member     = google_service_account.agent.member
}
