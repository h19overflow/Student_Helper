# Frontend Deployment Script
# Builds and deploys study-buddy-ai to S3 + CloudFront

param(
    [string]$Bucket = "student-helper-dev-frontend",
    [string]$Region = "ap-southeast-2",
    [string]$DistributionId = "",
    [switch]$SkipBuild,
    [switch]$InvalidateCache
)

$ErrorActionPreference = "Stop"

# Path setup - script is now in backend/scripts/
$ScriptLocation = Split-Path -Parent $MyInvocation.MyCommand.Path  # backend/scripts/
$BackendDir = Split-Path -Parent $ScriptLocation  # backend/
$ProjectRoot = Split-Path -Parent $BackendDir  # project root
$FrontendDir = Join-Path $ProjectRoot "study-buddy-ai"
$DistPath = Join-Path $FrontendDir "dist"

Write-Host "=== Frontend Deployment ===" -ForegroundColor Cyan

# Step 1: Build
if (-not $SkipBuild) {
    Write-Host "`n[1/3] Building frontend..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    try {
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "Build failed" }
    }
    finally {
        Pop-Location
    }
    Write-Host "Build complete!" -ForegroundColor Green
}
else {
    Write-Host "`n[1/3] Skipping build..." -ForegroundColor Gray
}

# Step 2: Upload to S3
Write-Host "`n[2/3] Uploading to S3..." -ForegroundColor Yellow

if (-not (Test-Path $DistPath)) {
    throw "dist/ folder not found at: $DistPath. Run build first."
}

aws s3 sync $DistPath "s3://$Bucket" `
    --region $Region `
    --delete `
    --cache-control "public, max-age=31536000, immutable" `
    --exclude "index.html" `
    --exclude "*.json"

# Upload index.html and JSON with no-cache
aws s3 cp "$DistPath/index.html" "s3://$Bucket/index.html" `
    --region $Region `
    --cache-control "no-cache, no-store, must-revalidate"

# Upload any JSON files (like manifest) with short cache
Get-ChildItem -Path $DistPath -Filter "*.json" | ForEach-Object {
    aws s3 cp $_.FullName "s3://$Bucket/$($_.Name)" `
        --region $Region `
        --cache-control "public, max-age=0, must-revalidate"
}

Write-Host "Upload complete!" -ForegroundColor Green

# Step 3: Invalidate CloudFront cache (optional)
if ($InvalidateCache -and $DistributionId) {
    Write-Host "`n[3/3] Invalidating CloudFront cache..." -ForegroundColor Yellow
    aws cloudfront create-invalidation `
        --distribution-id $DistributionId `
        --paths "/*" `
        --region $Region
    Write-Host "Cache invalidation started!" -ForegroundColor Green
}
else {
    Write-Host "`n[3/3] Skipping cache invalidation" -ForegroundColor Gray
}

Write-Host "`n=== Deployment Complete ===" -ForegroundColor Cyan
Write-Host "Frontend URL: https://dixngshe1kwme.cloudfront.net" -ForegroundColor White
