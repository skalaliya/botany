output "raw_bucket" {
  value = google_storage_bucket.raw_docs.name
}

output "cloudsql_instance" {
  value = google_sql_database_instance.postgres.name
}

output "api_service" {
  value = google_cloud_run_v2_service.api_gateway.name
}
