#!/bin/bash
# Entrypoint script - fetches RDS password from Secrets Manager if not set

set -e

# If POSTGRES_PASSWORD not set, fetch from Secrets Manager
if [ -z "$POSTGRES_PASSWORD" ]; then
    if [ -n "$AWS_REGION" ] && [ -n "$POSTGRES_SECRET_ID" ]; then
        echo "Fetching POSTGRES_PASSWORD from Secrets Manager..."
        export POSTGRES_PASSWORD=$(aws secretsmanager get-secret-value \
            --secret-id "$POSTGRES_SECRET_ID" \
            --region "$AWS_REGION" \
            --query SecretString \
            --output text | jq -r '.password')
    fi
fi

# Run uvicorn
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
