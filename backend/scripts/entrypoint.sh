#!/bin/bash
# Entrypoint script - initializes database and starts FastAPI
# Runs on every container start; table creation is idempotent (IF NOT EXISTS)

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

# Create database tables (idempotent - uses CREATE TABLE IF NOT EXISTS)
echo "Initializing database tables..."
python -m backend.boundary.db.create_tables
echo "Database initialization complete."

# Run uvicorn
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
