# A named database, not (default). The default database inherits an immutable
# project-wide resource location that may already have been set by something
# else, and a wrong location cannot be corrected without deleting the database.
# A named one always lands in var.region. The cost of that determinism is the
# free quota, which is worth a fraction of a cent at workshop volumes.
resource "google_firestore_database" "invoices" {
  name        = "invoices"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  # Both are needed for terraform destroy to actually remove the database.
  # deletion_policy defaults to ABANDON, which would leave it behind.
  deletion_policy         = "DELETE"
  delete_protection_state = "DELETE_PROTECTION_DISABLED"
}
