# Where the persistence tool archives the original document it analysed.
resource "google_storage_bucket" "archive" {
  # Bucket names are globally unique, so the project id is the disambiguator.
  name     = "${var.name}-${var.project_id}"
  location = var.region

  # Enforced by default on organizations created after 2024-05-03. Setting it
  # explicitly means the stack behaves identically inside and outside an org.
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  # A workshop bucket should not outlive the workshop, and terraform destroy
  # refuses to delete a bucket with objects in it.
  force_destroy = true

  lifecycle_rule {
    condition {
      age = 7
    }
    action {
      type = "Delete"
    }
  }
}
