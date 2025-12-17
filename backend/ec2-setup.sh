#!/bin/bash
# EC2 Backend Setup Script
# Run this on EC2 to pull and start the backend container

set -e

# Configuration
REGION="ap-southeast-2"
ACCOUNT_ID="575734508049"
REPO_NAME="student-helper-dev-backend"
TAG="latest"
CONTAINER_NAME="backend"

ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
IMAGE_URI="${ECR_URI}/${REPO_NAME}:${TAG}"

echo "=== EC2 Backend Setup ==="

# Step 1: Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "[1/5] Installing Docker..."
    sudo yum update -y
    sudo yum install -y docker
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker ec2-user
    echo "Docker installed. You may need to re-login for group changes."
else
    echo "[1/5] Docker already installed"
fi

# Step 2: Login to ECR
echo "[2/5] Logging into ECR..."
aws ecr get-login-password --region $REGION | sudo docker login --username AWS --password-stdin $ECR_URI

# Step 3: Pull latest image
echo "[3/5] Pulling image..."
sudo docker pull $IMAGE_URI

# Step 4: Stop existing container if running
echo "[4/5] Stopping existing container..."
sudo docker stop $CONTAINER_NAME 2>/dev/null || true
sudo docker rm $CONTAINER_NAME 2>/dev/null || true

# Step 5: Run container
echo "[5/5] Starting container..."
sudo docker run -d \
    --name $CONTAINER_NAME \
    --restart unless-stopped \
    -p 8000:8000 \
    -e POSTGRES_HOST="student-helper-dev-postgres.cn42mcooy4v2.ap-southeast-2.rds.amazonaws.com" \
    -e POSTGRES_PORT="5432" \
    -e POSTGRES_USER="postgres" \
    -e POSTGRES_PASSWORD="PLACEHOLDER_SET_VIA_CLI" \
    -e POSTGRES_DB="studenthelper" \
    -e AWS_REGION="ap-southeast-2" \
    -e DOCUMENTS_BUCKET="student-helper-dev-documents" \
    -e VECTORS_BUCKET="student-helper-dev-vectors" \
    -e VECTORS_INDEX="documents" \
    -e SQS_QUEUE_URL="https://sqs.ap-southeast-2.amazonaws.com/575734508049/student-helper-dev-doc-processor" \
    -e GOOGLE_API_KEY="${GOOGLE_API_KEY}" \
    -e LANGFUSE_SECRET_KEY="${LANGFUSE_SECRET_KEY}" \
    -e LANGFUSE_PUBLIC_KEY="${LANGFUSE_PUBLIC_KEY}" \
    -e LANGFUSE_BASE_URL="https://cloud.langfuse.com" \
    $IMAGE_URI

echo ""
echo "=== Setup Complete ==="
echo "Container status:"
sudo docker ps | grep $CONTAINER_NAME
echo ""
echo "View logs: sudo docker logs -f $CONTAINER_NAME"
echo "Health check: curl http://localhost:8000/api/v1/health"
