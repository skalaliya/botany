# Rollback Runbook

1. Identify last known good image tag (git SHA).
2. Run Cloud Run rollback:

```bash
gcloud run services update nexuscargo-prod-api-gateway \
  --region=australia-southeast1 \
  --image=australia-southeast1-docker.pkg.dev/<project>/<repo>/api-gateway:<known-good-sha>
```

3. Run database rollback only if migration is backward compatible and tested:

```bash
alembic downgrade -1
```

4. Confirm health checks and critical workflows.
