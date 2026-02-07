# Production Deployment Guide

## 1) Preconditions
1. Terraform variables for target environment are set.
2. Secret Manager contains required secrets:
   - auth jwt/refresh
   - webhook signing
   - provider API tokens
3. Cloud SQL connection string is available in CI secrets.

## 2) Deploy Infrastructure
```bash
cd infra/terraform
terraform init
terraform apply -var project_id=<gcp-project> -var environment=prod
```

## 3) Build and Push Artifacts
```bash
docker build -t nexuscargo-api:<git-sha> -f ops/docker/api-gateway.Dockerfile .
# push to Artifact Registry as configured in terraform
```

## 4) Apply Database Migrations
```bash
DATABASE_URL=<prod-connection-string> alembic upgrade head
```

## 5) Rollout Services/Jobs
1. Deploy API gateway Cloud Run service.
2. Deploy analytics and webhook worker Cloud Run jobs.
3. Validate `/healthz` and `/readyz`.

## 6) Post-Deploy Validation
1. Trigger ingestion smoke flow and confirm review routing.
2. Trigger webhook dispatch and worker run; confirm no unexpected DLQ growth.
3. Verify station analytics transform endpoint.
4. Verify active learning model register/list/rollback endpoints.

## 7) Rollback
- Follow `/Users/samkalaliya/Documents/BOTANY/ops/runbooks/rollback.md`.
