"""
Build and push Lambda Docker image to ECR.

Usage:
    .\build-lambda-image.ps1 -Environment dev
    .\build-lambda-image.ps1 -Environment prod -Push $true

Parameters:
    -Environment: Deployment environment (dev, staging, prod)
    -Push: Push to ECR after build (default: $false for local testing)
    -SkipBuild: Skip build, only push (default: $false)
"""

param(
    [Parameter(Mandatory=$true)]
    [string]$Environment,

    [Parameter(Mandatory=$false)]
    [bool]$Push = $false,

    [Parameter(Mandatory=$false)]
    [bool]$SkipBuild = $false
)

$ErrorActionPreference = "Stop"

# Configuration
$PROJECT_ROOT = Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$LAMBDA_DIR = Join-Path $PROJECT_ROOT "backend\core\document_processing"
$IMAGE_NAME = "student-helper-lambda-processor"
$IMAGE_TAG = "latest"

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "Lambda Docker Build Script" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
Write-Host "Environment: $Environment" -ForegroundColor Yellow
Write-Host "Lambda Directory: $LAMBDA_DIR" -ForegroundColor Yellow
Write-Host "Image Name: $IMAGE_NAME" -ForegroundColor Yellow
Write-Host ""

# Verify Dockerfile exists
if (-not (Test-Path "$LAMBDA_DIR\Dockerfile")) {
    Write-Host "ERROR: Dockerfile not found at $LAMBDA_DIR\Dockerfile" -ForegroundColor Red
    exit 1
}

# Build image locally
if (-not $SkipBuild) {
    Write-Host "Building Docker image..." -ForegroundColor Cyan
    Write-Host "Command: docker build -t ${IMAGE_NAME}:${IMAGE_TAG} -f $LAMBDA_DIR\Dockerfile $LAMBDA_DIR" -ForegroundColor DarkGray
    Write-Host ""

    Push-Location $LAMBDA_DIR
    try {
        docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" -f "$LAMBDA_DIR\Dockerfile" $LAMBDA_DIR
        if ($LASTEXITCODE -ne 0) {
            throw "Docker build failed"
        }
        Write-Host "✓ Docker image built successfully" -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
}

# Push to ECR if requested
if ($Push) {
    Write-Host ""
    Write-Host "Pushing to ECR..." -ForegroundColor Cyan

    # Get AWS account ID and region from stack
    Write-Host "Retrieving ECR repository URL from Pulumi..." -ForegroundColor DarkGray

    try {
        $stackInfo = pulumi stack output -s "student-helper/$Environment" --json 2>$null | ConvertFrom-Json
        $ECR_REPOSITORY_URL = $stackInfo.ecr_repository_url
        $AWS_REGION = $stackInfo.aws_region

        if (-not $ECR_REPOSITORY_URL) {
            throw "Could not retrieve ECR repository URL from Pulumi stack"
        }
    }
    catch {
        Write-Host "ERROR: $($_)" -ForegroundColor Red
        Write-Host ""
        Write-Host "To push to ECR, ensure Pulumi stack outputs include:" -ForegroundColor Yellow
        Write-Host "  - ecr_repository_url" -ForegroundColor Yellow
        Write-Host "  - aws_region" -ForegroundColor Yellow
        exit 1
    }

    Write-Host "ECR Repository URL: $ECR_REPOSITORY_URL" -ForegroundColor Yellow
    Write-Host ""

    # Authenticate with ECR
    Write-Host "Authenticating with ECR..." -ForegroundColor DarkGray
    $AWS_ACCOUNT_ID = $ECR_REPOSITORY_URL.Split('.')[0]
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

    if ($LASTEXITCODE -ne 0) {
        throw "ECR authentication failed"
    }

    # Tag image for ECR
    $ECR_IMAGE_TAG = "$ECR_REPOSITORY_URL:latest"
    Write-Host "Tagging image: $ECR_IMAGE_TAG" -ForegroundColor DarkGray
    docker tag "${IMAGE_NAME}:${IMAGE_TAG}" "$ECR_IMAGE_TAG"

    # Push image
    Write-Host "Pushing image to ECR..." -ForegroundColor DarkGray
    docker push "$ECR_IMAGE_TAG"

    if ($LASTEXITCODE -ne 0) {
        throw "Docker push to ECR failed"
    }

    Write-Host "✓ Image pushed successfully" -ForegroundColor Green
    Write-Host ""
    Write-Host "ECR Image URI: $ECR_IMAGE_TAG" -ForegroundColor Green
}

Write-Host ""
Write-Host "✓ Build process completed successfully" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Run: cd .\IAC && pulumi up -s student-helper/$Environment" -ForegroundColor DarkGray
Write-Host "  2. Verify Lambda function uses the new image" -ForegroundColor DarkGray
