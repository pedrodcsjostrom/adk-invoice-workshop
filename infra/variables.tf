variable "project_id" {
  description = "Your own Google Cloud project. Nothing should be in it beyond the pre-flight API enablement."
  type        = string
}

variable "region" {
  description = "Where Cloud Run, Artifact Registry, Firestore and the bucket live."
  type        = string
  default     = "europe-west1"
}

# Deliberately not var.region. No single region serves a Gemini 3.x model, so
# the infrastructure region and the model endpoint cannot be one variable.
# See docs/research/gcp-project-preflight-and-cost.md, section 5.
variable "model_location" {
  description = "Vertex AI endpoint the agent calls. Only the global endpoint serves gemini-3.5-flash."
  type        = string
  default     = "global"
}

variable "model" {
  description = "Gemini model the agent runs on."
  type        = string
  default     = "gemini-3.5-flash"
}

# On the first apply there is no agent image: Artifact Registry is created by
# this same stack. The service starts on Google's public hello container, so
# the stack and the proxy are provable before any code is built. Build, push,
# then re-apply with -var image=... to swap in the real agent.
variable "image" {
  description = "Container image the Cloud Run service runs."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "name" {
  description = "Prefix for every resource this stack creates."
  type        = string
  default     = "invoice-agent"
}
