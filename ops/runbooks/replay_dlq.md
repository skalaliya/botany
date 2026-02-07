# DLQ Replay Runbook

```bash
# Example replay for document.received DLQ
PROJECT_ID="your-project"
SUB="nexuscargo-prod-document-received-dlq-sub"
TOPIC="nexuscargo-prod-document-received"

gcloud pubsub subscriptions pull "$SUB" --project "$PROJECT_ID" --limit=100 --auto-ack --format=json > dlq.json
jq -c '.[] | .message.data' dlq.json | while read -r encoded; do
  gcloud pubsub topics publish "$TOPIC" --project "$PROJECT_ID" --message="$(echo "$encoded" | base64 --decode)"
done
```
