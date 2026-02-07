# Model Rollback Runbook

1. Identify the impacted domain/model from monitoring or review drift.
2. Fetch model versions:
```bash
curl -H "Authorization: Bearer <token>" -H "X-Tenant-Id: <tenant>" \
  "<api>/api/v1/active-learning/models?domain=<domain>"
```
3. Execute rollback:
```bash
curl -X POST -H "Authorization: Bearer <token>" -H "X-Tenant-Id: <tenant>" \
  "<api>/api/v1/active-learning/models/<model_id>/rollback"
```
4. Confirm `model_registry.rolled_back` audit event and monitor extraction quality.
