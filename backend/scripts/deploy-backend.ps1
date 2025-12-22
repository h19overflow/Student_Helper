# Backend ECR Deployment Script
# Builds and pushes backend Docker image to ECR

param(
    [string]$Region = "ap-southeast-2",
    [string]$RepoName = "student-helper-dev-backend",
    [string]$Tag = "latest"
)

$ErrorActionPreference = "Stop"

# Path setup - script is now in backend/scripts/
$ScriptLocation = Split-Path -Parent $MyInvocation.MyCommand.Path  # backend/scripts/
$BackendDir = Split-Path -Parent $ScriptLocation  # backend/
$ProjectRoot = Split-Path -Parent $BackendDir  # project root

Write-Host "=== Backend ECR Deployment ===" -ForegroundColor Cyan

# Step 1: Get AWS Account ID
Write-Host "`n[1/5] Getting AWS account info..." -ForegroundColor Yellow
$AccountId = aws sts get-caller-identity --query Account --output text
if (-not $AccountId) { throw "Failed to get AWS account ID" }
Write-Host "Account ID: $AccountId" -ForegroundColor Green

$EcrUri = "$AccountId.dkr.ecr.$Region.amazonaws.com"
$ImageUri = "$EcrUri/$RepoName`:$Tag"

# Step 2: Create ECR repository if it doesn't exist
Write-Host "`n[2/5] Ensuring ECR repository exists..." -ForegroundColor Yellow
$RepoExists = aws ecr describe-repositories --repository-names $RepoName --region $Region 2>$null
if (-not $RepoExists) {
    Write-Host "Creating repository: $RepoName" -ForegroundColor Yellow
    aws ecr create-repository `
        --repository-name $RepoName `
        --region $Region `
        --image-scanning-configuration scanOnPush=true `
        --encryption-configuration encryptionType=AES256
}
Write-Host "Repository ready: $RepoName" -ForegroundColor Green

# Step 3: Login to ECR
Write-Host "`n[3/5] Logging into ECR..." -ForegroundColor Yellow
aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $EcrUri
if ($LASTEXITCODE -ne 0) { throw "ECR login failed" }
Write-Host "ECR login successful" -ForegroundColor Green

# Step 4: Build Docker image
Write-Host "`n[4/5] Building Docker image..." -ForegroundColor Yellow
Push-Location $BackendDir
try {
    # Copy configs folder for build context if needed
    if (-not (Test-Path "$BackendDir/configs")) {
        Copy-Item -Path "$ProjectRoot/backend/configs" -Destination "$BackendDir/configs" -Recurse -ErrorAction SilentlyContinue
    }

    docker build -t $RepoName`:$Tag .
    if ($LASTEXITCODE -ne 0) { throw "Docker build failed" }
}
finally {
    Pop-Location
}
Write-Host "Build complete" -ForegroundColor Green

# Step 5: Tag and push
Write-Host "`n[5/5] Pushing to ECR..." -ForegroundColor Yellow
docker tag $RepoName`:$Tag $ImageUri
docker push $ImageUri
if ($LASTEXITCODE -ne 0) { throw "Docker push failed" }

Write-Host "`n=== Deployment Complete ===" -ForegroundColor Cyan
Write-Host "Image URI: $ImageUri" -ForegroundColor White
Write-Host "`nTo pull on EC2:" -ForegroundColor Gray
Write-Host "  aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $EcrUri" -ForegroundColor Gray
Write-Host "  docker pull $ImageUri" -ForegroundColor Gray
