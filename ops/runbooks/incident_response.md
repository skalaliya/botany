# Incident Response Runbook

1. Identify impacted tenant(s), service(s), and SLO breach in Cloud Monitoring dashboards.
2. Freeze deployments to production environment.
3. Triage by severity:
   - P0 data leakage or auth bypass -> revoke tokens, rotate secrets in Secret Manager, isolate impacted services.
   - P1 processing outage -> scale Cloud Run services and replay Pub/Sub dead-letter events.
4. Capture immutable timeline in `audit_events` and incident doc.
5. Apply hotfix through CI/CD with staging verification before prod rollout.
