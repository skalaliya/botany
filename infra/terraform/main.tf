provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  name_prefix = "nexuscargo-${var.environment}"

  event_topics = [
    "document.received",
    "document.preprocessed",
    "document.classified",
    "document.extracted",
    "document.validated",
    "review.required",
    "review.completed",
    "discrepancy.detected",
    "export.submission.updated",
    "invoice.dispute.updated"
  ]
}

resource "google_compute_network" "vpc" {
  name                    = "${local.name_prefix}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "${local.name_prefix}-subnet"
  ip_cidr_range = "10.42.0.0/20"
  region        = var.region
  network       = google_compute_network.vpc.id
}

resource "google_compute_firewall" "allow_https" {
  name    = "${local.name_prefix}-allow-https"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }

  source_ranges = var.allowed_ingress_cidrs
}

resource "google_storage_bucket" "raw_docs" {
  name                        = "${local.name_prefix}-raw-docs"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true

  lifecycle_rule {
    action {
      type = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
    condition {
      age = 365
    }
  }
}

resource "google_storage_bucket" "processed_docs" {
  name                        = "${local.name_prefix}-processed-docs"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "audit_archive" {
  name                        = "${local.name_prefix}-audit-archive"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true

  retention_policy {
    retention_period = 220752000
  }
}

resource "google_sql_database_instance" "postgres" {
  name             = "${local.name_prefix}-sql"
  region           = var.region
  database_version = "POSTGRES_16"

  settings {
    tier = var.cloudsql_tier

    backup_configuration {
      enabled = true
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
    }
  }

  deletion_protection = true
}

resource "google_sql_database" "app_db" {
  name     = "nexuscargo"
  instance = google_sql_database_instance.postgres.name
}

resource "google_pubsub_topic" "events" {
  for_each = toset(local.event_topics)
  name     = "${local.name_prefix}-${replace(each.value, ".", "-")}"
}

resource "google_pubsub_topic" "dlq" {
  for_each = toset(local.event_topics)
  name     = "${local.name_prefix}-${replace(each.value, ".", "-")}-dlq"
}

resource "google_pubsub_subscription" "events_subscriptions" {
  for_each = google_pubsub_topic.events
  name     = "${each.value.name}-sub"
  topic    = each.value.id

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq[each.key].id
    max_delivery_attempts = 10
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

resource "google_pubsub_subscription" "dlq_replay_subscriptions" {
  for_each = google_pubsub_topic.dlq
  name     = "${each.value.name}-replay-sub"
  topic    = each.value.id

  retry_policy {
    minimum_backoff = "30s"
    maximum_backoff = "600s"
  }
}

resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "${local.name_prefix}-containers"
  format        = "DOCKER"
}

resource "google_redis_instance" "cache" {
  name               = "${local.name_prefix}-redis"
  tier               = "STANDARD_HA"
  memory_size_gb     = 2
  region             = var.region
  location_id        = "${var.region}-a"
  authorized_network = google_compute_network.vpc.id
}

resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "${local.name_prefix}-auth-jwt-secret"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "refresh_secret" {
  secret_id = "${local.name_prefix}-auth-refresh-secret"

  replication {
    auto {}
  }
}

resource "google_bigquery_dataset" "analytics" {
  dataset_id                 = "nexuscargo_analytics_${var.environment}"
  location                   = var.region
  delete_contents_on_destroy = false
}

resource "google_cloud_run_v2_service" "api_gateway" {
  name     = "${local.name_prefix}-api-gateway"
  location = var.region

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}/api-gateway:latest"
      env {
        name  = "EVENT_BUS_BACKEND"
        value = "pubsub"
      }
    }

    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }
  }
}

resource "google_cloud_run_v2_job" "analytics_job" {
  name     = "${local.name_prefix}-analytics-job"
  location = var.region

  template {
    template {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}/analytics-job:latest"
      }
      max_retries = 3
    }
  }
}

resource "google_cloud_run_v2_job" "webhook_worker_job" {
  name     = "${local.name_prefix}-webhook-worker"
  location = var.region

  template {
    template {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}/webhook-worker:latest"
      }
      max_retries = 3
    }
  }
}

resource "google_monitoring_alert_policy" "error_rate" {
  display_name = "${local.name_prefix} API error rate"
  combiner     = "OR"

  conditions {
    display_name = "Cloud Run 5xx ratio"
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
}

resource "google_monitoring_alert_policy" "latency_p95" {
  display_name = "${local.name_prefix} API latency p95"
  combiner     = "OR"

  conditions {
    display_name = "Cloud Run request latencies"
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_latencies\" AND resource.type=\"cloud_run_revision\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 1.0

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_PERCENTILE_95"
      }
    }
  }
}

resource "google_monitoring_alert_policy" "dlq_backlog" {
  display_name = "${local.name_prefix} DLQ backlog"
  combiner     = "OR"

  conditions {
    display_name = "PubSub DLQ messages"
    condition_threshold {
      filter          = "metric.type=\"pubsub.googleapis.com/subscription/num_undelivered_messages\" AND resource.type=\"pubsub_subscription\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 100

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
}
