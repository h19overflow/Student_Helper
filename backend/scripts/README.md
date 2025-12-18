# Deployment Scripts

All deployment scripts consolidated here for easy access.

## Scripts

### 1. `deploy-backend.ps1`
Build and push backend Docker image to ECR.

```powershell
# Deploy backend with defaults
.\backend\scripts\deploy-backend.ps1

# Deploy with custom tag
.\backend\scripts\deploy-backend.ps1 -Tag "v1.2.3"

# Deploy to different region
.\backend\scripts\deploy-backend.ps1 -Region "us-east-1"
```

**What it does:**
- Builds Docker image from `backend/Dockerfile`
- Pushes to ECR repository
- Tags as `latest` by default

---

### 2. `deploy-frontend.ps1`
Build and deploy React frontend to S3 + CloudFront.

```powershell
# Build and deploy frontend
.\backend\scripts\deploy-frontend.ps1

# Deploy without rebuilding
.\backend\scripts\deploy-frontend.ps1 -SkipBuild

# Deploy and invalidate CloudFront cache
.\backend\scripts\deploy-frontend.ps1 -InvalidateCache -DistributionId "E1234567890ABC"
```

**What it does:**
- Builds React app from `study-buddy-ai/`
- Uploads to S3 bucket
- Optionally invalidates CloudFront cache

---

### 3. `ec2-setup.sh`
Run on EC2 instance to pull and start backend container.

```bash
# On your local machine, copy to EC2
scp backend/scripts/ec2-setup.sh ec2-user@<ec2-ip>:~/

# SSH to EC2 and run
ssh ec2-user@<ec2-ip>
chmod +x ec2-setup.sh
./ec2-setup.sh
```

**What it does:**
- Installs Docker if needed
- Pulls latest image from ECR
- Starts backend container on port 8000

---

## Deployment Workflow

### Full Stack Deployment

```powershell
# 1. Deploy infrastructure (if needed)
cd IAC
pulumi up

# 2. Deploy backend
.\backend\scripts\deploy-backend.ps1

# 3. Update EC2 (SSH to instance)
ssh ec2-user@<ec2-ip>
./ec2-setup.sh

# 4. Deploy frontend
.\backend\scripts\deploy-frontend.ps1 -InvalidateCache -DistributionId "E..."
```

### Quick Updates

**Backend code change:**
```powershell
.\backend\scripts\deploy-backend.ps1
# Then SSH to EC2 and run: ./ec2-setup.sh
```

**Frontend code change:**
```powershell
.\backend\scripts\deploy-frontend.ps1 -InvalidateCache -DistributionId "E..."
```

**Infrastructure change:**
```powershell
cd IAC
pulumi up
```

---

## Environment Variables

### Backend (`ec2-setup.sh`)
Set these on EC2 before running:
```bash
export GOOGLE_API_KEY="your-key"
export LANGFUSE_SECRET_KEY="your-key"
export LANGFUSE_PUBLIC_KEY="your-key"
```

### Frontend
Set in `.env.production`:
```
VITE_API_BASE_URL=https://your-api-gateway-url
```

---

## Troubleshooting

### Backend deployment fails
- Check AWS credentials: `aws sts get-caller-identity`
- Ensure ECR repository exists
- Check Docker is running

### Frontend deployment fails
- Check S3 bucket exists and is accessible
- Verify npm build succeeds locally
- Check AWS credentials have S3 permissions

### EC2 setup fails
- Ensure EC2 has IAM role with ECR pull permissions
- Check security groups allow traffic on port 8000
- Verify Docker is installed: `docker --version`

---

## Quick Reference

| Task | Command |
|------|---------|
| Deploy backend | `.\backend\scripts\deploy-backend.ps1` |
| Deploy frontend | `.\backend\scripts\deploy-frontend.ps1` |
| Update EC2 | SSH + `./ec2-setup.sh` |
| View backend logs | `sudo docker logs -f backend` |
| Check health | `curl http://localhost:8000/api/v1/health` |
