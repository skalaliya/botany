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
            query = (
                "CREATE OR REPLACE TABLE `"
                f"{self._settings.gcp_project_id}.nexuscargo_analytics_{self._settings.environment}.station_kpi_daily` "
                "AS SELECT CURRENT_DATE() AS as_of_date, 0 AS placeholder_metric"
            )
            client.query(query).result()
            return "ok:transform_executed"
        except Exception:
            return "failed:transform_execution_error"
