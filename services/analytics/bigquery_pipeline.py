from __future__ import annotations

import importlib

from libs.common.config import Settings, get_settings


class BigQueryPipeline:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def run_station_analytics_transform(self) -> str:
        if not self._settings.gcp_project_id:
            return "skipped:no_gcp_project"
        if self._settings.environment == "dev":
            return "skipped:dev_environment"

        try:
            bigquery_module = importlib.import_module("google.cloud.bigquery")
            client = bigquery_module.Client(project=self._settings.gcp_project_id)
            kpi_table = (
                f"{self._settings.gcp_project_id}."
                f"nexuscargo_analytics_{self._settings.environment}.station_kpi_daily"
            )
            query = (
                "CREATE OR REPLACE TABLE `"
                f"{kpi_table}` "
                "AS SELECT "
                "CURRENT_DATE() AS as_of_date, "
                "COUNT(1) AS processed_documents, "
                "0 AS delayed_documents, "
                "0.0 AS sla_risk, "
                "\"none\" AS bottleneck_indicator "
                f"FROM `{self._settings.gcp_project_id}.nexuscargo_analytics_{self._settings.environment}.__TABLES__`"
            )
            client.query(query).result()
            return "ok:transform_executed"
        except Exception:
            return "failed:transform_execution_error"

    def query_latest_station_kpi(self) -> dict[str, object]:
        if not self._settings.gcp_project_id or self._settings.environment == "dev":
            return {
                "as_of_date": None,
                "processed_documents": 0,
                "delayed_documents": 0,
                "sla_risk": 0.0,
                "bottleneck_indicator": "none",
                "source": "local_fallback",
            }

        try:
            bigquery_module = importlib.import_module("google.cloud.bigquery")
            client = bigquery_module.Client(project=self._settings.gcp_project_id)
            query = (
                "SELECT as_of_date, processed_documents, delayed_documents, sla_risk, bottleneck_indicator "
                f"FROM `{self._settings.gcp_project_id}.nexuscargo_analytics_{self._settings.environment}.station_kpi_daily` "
                "ORDER BY as_of_date DESC LIMIT 1"
            )
            rows = list(client.query(query).result())
            if not rows:
                return {
                    "as_of_date": None,
                    "processed_documents": 0,
                    "delayed_documents": 0,
                    "sla_risk": 0.0,
                    "bottleneck_indicator": "none",
                    "source": "bigquery_empty",
                }
            row = rows[0]
            return {
                "as_of_date": str(row["as_of_date"]),
                "processed_documents": int(row["processed_documents"]),
                "delayed_documents": int(row["delayed_documents"]),
                "sla_risk": float(row["sla_risk"]),
                "bottleneck_indicator": str(row["bottleneck_indicator"]),
                "source": "bigquery",
            }
        except Exception:
            return {
                "as_of_date": None,
                "processed_documents": 0,
                "delayed_documents": 0,
                "sla_risk": 0.0,
                "bottleneck_indicator": "none",
                "source": "bigquery_error",
            }
