# Lambda Deployment Script Refactor Plan

**Status:** In Planning
**Date Created:** 2025-12-22
**Objective:** Consolidate deployment scripts, fix Docker build context, ensure consistent redeployment

---

## 📚 Plan Structure

This refactor is broken into **5 executable phases**, each with its own file:

```
documentation/07_lambda_deployment_refactor/
├── README.md                              (This file - navigation)
├── QUICK_REFERENCE.md                     (Copy-paste commands by environment)
├── VERIFICATION_CHECKLIST.md              (Go/no-go checklist for each phase)
├── ROLLBACK_GUIDE.md                      (How to undo if things break)
│
├── PHASE_0_PREPARATION.md                 (Setup & validation - 5 min)
├── PHASE_1_SCRIPT_CONSOLIDATION.md        (Keep Python, delete PowerShell - 15 min)
├── PHASE_2_INFRASTRUCTURE_FIXES.md        (Fix Dockerfile, entrypoint - 10 min)
├── PHASE_3_TESTING_VALIDATION.md          (Test locally - 20 min)
├── PHASE_4_DOCUMENTATION_CLEANUP.md       (Update guides - 20 min)
└── PHASE_5_PRODUCTION_DEPLOYMENT.md       (Deploy to staging/prod - 30 min)
```

---

## 🎯 Quick Start

### If you're in a hurry (just build & push):
See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) → Copy the command for your environment

### If you're doing the full refactor:
1. Read [VERIFICATION_CHECKLIST.md](VERIFICATION_CHECKLIST.md) - Know what success looks like
2. Execute each phase in order (Phase 0 → Phase 5)
3. After each phase, use [VERIFICATION_CHECKLIST.md](VERIFICATION_CHECKLIST.md) to verify
4. If something breaks, see [ROLLBACK_GUIDE.md](ROLLBACK_GUIDE.md)

---

## 📋 Phase Overview

### [Phase 0: Preparation](PHASE_0_PREPARATION.md) - **5 minutes**
**Goal:** Verify environment and create rollback checkpoint

- ✅ Check boto3 in requirements
- ✅ Create git checkpoint
- ✅ List current scripts

**When complete:** Safe to proceed with code changes

---

### [Phase 1: Script Consolidation](PHASE_1_SCRIPT_CONSOLIDATION.md) - **15 minutes**
**Goal:** Delete PowerShell, fix Python script

**Changes:**
- 🗑️ DELETE `backend/scripts/build-lambda-image.ps1`
- ✏️ FIX `backend/scripts/ecr_builder.py` (3 specific changes)
- 📝 UPDATE `backend/scripts/LAMBDA_DEPLOYMENT_GUIDE.md`

**When complete:** Single Python deployment script, no duplicate tools

---

### [Phase 2: Infrastructure Fixes](PHASE_2_INFRASTRUCTURE_FIXES.md) - **10 minutes**
**Goal:** Fix Docker build context and runtime dependencies

**Changes:**
- ✏️ FIX `backend/core/document_processing/Dockerfile` (remove 1 line)
- ✏️ FIX `backend/scripts/entrypoint.sh` (replace bash with Python/boto3)

**When complete:** Docker image builds without errors

---

### [Phase 3: Testing & Validation](PHASE_3_TESTING_VALIDATION.md) - **20 minutes**
**Goal:** Verify everything works locally

**Tests:**
- 🧪 Build image: `python -m scripts.ecr_builder build --environment dev`
- 🧪 Verify image: `docker images | grep student-helper`
- 🧪 Check Pulumi: `pulumi stack select student-helper/dev`

**When complete:** Image builds reliably, ready for deployment

---

### [Phase 4: Documentation Cleanup](PHASE_4_DOCUMENTATION_CLEANUP.md) - **20 minutes**
**Goal:** Update all guides to remove PowerShell references

**Changes:**
- 📝 UPDATE `backend/scripts/LAMBDA_DEPLOYMENT_GUIDE.md` (remove 3 sections)
- 📝 UPDATE `backend/scripts/README.md`
- ✨ CREATE `documentation/07_lambda_deployment_refactor/DEPLOYMENT_RUNBOOK.md`
- 📝 UPDATE `documentation/README.md`

**When complete:** All documentation reflects Python-only approach

---

### [Phase 5: Production Deployment](PHASE_5_PRODUCTION_DEPLOYMENT.md) - **30 minutes**
**Goal:** Deploy to staging and production

**Steps:**
- 🚀 Build & push to staging ECR
- ✅ Deploy staging Lambda
- 🧪 Test in staging
- 🚀 Build & push to production ECR
- ✅ Deploy production Lambda
- 📊 Monitor in CloudWatch

**When complete:** New deployment process validated in production

---

## 🔄 Execution Flow

```
START
  ↓
[Phase 0] Preparation
  ├─ Verify environment
  └─ Create git checkpoint
  ↓
[Phase 1] Script Consolidation
  ├─ Delete PowerShell script
  ├─ Fix Python script
  └─ Update guides
  ↓
[Phase 2] Infrastructure Fixes
  ├─ Fix Dockerfile
  └─ Fix entrypoint.sh
  ↓
[Phase 3] Testing & Validation
  ├─ Build image
  ├─ Verify image
  └─ Test integration
  ↓
[Phase 4] Documentation Cleanup
  ├─ Update all .md files
  └─ Create runbook
  ↓
[Phase 5] Production Deployment
  ├─ Deploy staging
  ├─ Test staging
  ├─ Deploy production
  └─ Monitor
  ↓
SUCCESS ✅
```

---

## ⚠️ If Something Goes Wrong

**At any point**, use [ROLLBACK_GUIDE.md](ROLLBACK_GUIDE.md) to restore:

```bash
# Restore from checkpoint created in Phase 0
git reset --hard <checkpoint-commit>
```

---

## 📊 Success Metrics

| Metric | Target |
|--------|--------|
| **Build success rate** | 100% across all environments |
| **Docker build time** | < 5 minutes |
| **Script execution time** | < 2 minutes (build-and-push) |
| **Cross-platform support** | Windows, Linux, macOS, CI/CD |
| **External dependencies** | Zero (boto3 only, native to Lambda) |
| **Documentation clarity** | One runbook, not 3 variants |

---

## 📞 Key Files & Links

| Need | File |
|------|------|
| 🚀 Just want to deploy? | [QUICK_REFERENCE.md](QUICK_REFERENCE.md) |
| ✅ Need to verify completion? | [VERIFICATION_CHECKLIST.md](VERIFICATION_CHECKLIST.md) |
| 🔄 Need to undo changes? | [ROLLBACK_GUIDE.md](ROLLBACK_GUIDE.md) |
| 📚 Ready to execute? | Start with [PHASE_0_PREPARATION.md](PHASE_0_PREPARATION.md) |

---

## 👥 For Different Roles

### 👨‍💻 **Developer (Running locally)**
1. Start: [PHASE_0_PREPARATION.md](PHASE_0_PREPARATION.md)
2. When building: Use [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
3. If refactoring: Execute all phases in order

### 🔧 **DevOps/Infrastructure**
1. Review: All 5 phase files for impact
2. Approve: Changes to Dockerfile, entrypoint, scripts
3. Monitor: Phase 5 production deployment

### 📖 **Tech Lead**
1. Skim: This README + [VERIFICATION_CHECKLIST.md](VERIFICATION_CHECKLIST.md)
2. Check: Success criteria in each phase
3. Validate: Phase 5 metrics

---

---

## 🎓 Learn More

- **AWS Lambda with Docker:** https://docs.aws.amazon.com/lambda/latest/dg/images-create.html
- **ECR Best Practices:** https://docs.aws.amazon.com/AmazonECR/latest/userguide/best_practices.html
- **Pulumi Lambda:** https://www.pulumi.com/docs/reference/pkg/aws/lambda/

---

**Document Version:** 1.0
**Last Updated:** 2025-12-22
**Owner:** Development Team
**Status:** Ready for Execution
