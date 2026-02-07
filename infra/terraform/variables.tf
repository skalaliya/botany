variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "Primary region"
  default     = "australia-southeast1"
}

variable "environment" {
  type        = string
  description = "Deployment environment (dev/staging/prod)"
}

variable "cloudsql_tier" {
  type        = string
  default     = "db-custom-2-7680"
}

variable "allowed_ingress_cidrs" {
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
