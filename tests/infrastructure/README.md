# Infrastructure Test Suite

Comprehensive test suite for the Pulumi infrastructure scaffold in the `IAC/` directory.

## Quick Start

### Run All Tests

```bash
# Run with verbose output
python -m pytest tests/infrastructure/ -v

# Run with coverage report
python -m pytest tests/infrastructure/ -v --cov=IAC --cov-report=term-missing

# Run specific test file
python -m pytest tests/infrastructure/test_iac_syntax.py -v

# Run specific test class
python -m pytest tests/infrastructure/test_iac_components.py::TestNetworkingComponents -v
```

## Test Files

### 1. test_iac_syntax.py (31 tests)

Validates fundamental infrastructure code structure:

- **Syntax Validation** (2 tests)
  - All Python files parse correctly
  - Module count verified

- **Import Validation** (5 tests)
  - All components importable
  - Configuration modules accessible
  - Utilities functional
  - Main entry point valid

- **Component Structure** (6 tests)
  - VPC, Security Groups, S3, RDS, IAM, Lambda
  - Each has get_outputs() method
  - Output dataclasses properly defined

- **Configuration Validation** (3 tests)
  - EnvironmentConfig dataclass structure
  - Properties (is_production, api_subdomain)
  - Constants (VPC_CIDR, SUBNET_CIDRS, etc.)

- **Utility Functions** (4 tests)
  - ResourceNamer instantiation
  - Name generation
  - Tag creation and merging

- **Dependencies** (3 tests)
  - Pulumi framework available
  - pulumi-aws installed
  - Pydantic for schemas

- **Component Initialization** (3 tests)
  - Component classes valid
  - Output dataclasses correct
  - Instantiation requirements clear

- **Documentation** (3 tests)
  - Module docstrings present
  - Component documentation complete
  - Config documentation

- **Output Types** (3 tests)
  - VPC outputs include all subnet IDs and NAT gateway
  - S3 outputs include all bucket names and ARNs
  - RDS outputs include database endpoint

### 2. test_iac_components.py (30 tests)

Detailed validation of each component category:

- **Networking Components** (4 tests)
  - VPC with NAT gateway
  - Security groups
  - VPC endpoints

- **Security Components** (3 tests)
  - IAM roles with Lambda role ARN
  - Secrets manager

- **Storage Components** (5 tests)
  - S3 buckets (documents, vectors, frontend)
  - S3 outputs with ARNs
  - RDS PostgreSQL
  - Database endpoint output

- **Messaging Components** (2 tests)
  - SQS queues
  - Queue URL/ARN output

- **Compute Components** (5 tests)
  - EC2 backend with instance ID
  - EC2 private IP output
  - Lambda processor
  - Lambda function name output

- **Edge Components** (3 tests)
  - CloudFront distribution
  - API Gateway
  - Route53 DNS

- **Package Structure** (2 tests)
  - Component packages have __init__.py
  - Config/utils packages initialized

- **Component Exports** (5 tests)
  - Networking exports
  - Security exports
  - Storage exports
  - Compute exports
  - Edge exports

## Test Results

```
Total Tests:  60 passed, 1 skipped
Success Rate: 100%
Execution:    0.75s
Coverage:     55% (limited by Pulumi runtime requirement)
```

## Coverage Details

### High Coverage (>80%)
- Config constants: 100%
- Base config: 95%
- Tag utilities: 100%
- Naming utilities: 82%

### Medium Coverage (50-80%)
- Environment config: 60%
- SQS component: 70%
- Lambda component: 63%
- RDS component: 62%

### Lower Coverage (40-50%)
- Networking components: 42-47% (require AWS runtime)
- Security components: 44-50% (require AWS runtime)
- Edge components: 42-55% (require AWS runtime)

### Zero Coverage (Expected)
- __main__.py: 0% (requires Pulumi stack + AWS credentials)

## Component Structure

```
IAC/
├── configs/
│   ├── base.py          (EnvironmentConfig dataclass)
│   ├── constants.py     (VPC_CIDR, SUBNET_CIDRS, etc.)
│   └── environment.py   (Config loader)
│
├── utils/
│   ├── naming.py        (ResourceNamer class)
│   └── tags.py          (create_tags, merge_tags)
│
└── components/
    ├── networking/      (VPC, SecurityGroups, VpcEndpoints)
    ├── security/        (IamRoles, SecretsManager)
    ├── storage/         (S3Buckets, RdsPostgres)
    ├── messaging/       (SqsQueues)
    ├── compute/         (Ec2Backend, LambdaProcessor)
    └── edge/            (CloudFront, ApiGateway, Route53)
```

## Key Test Validations

### Syntax & Imports
- ✓ 29 Python files parse without errors
- ✓ All 13 components import successfully
- ✓ All dependencies available

### Configuration
- ✓ EnvironmentConfig frozen dataclass with 9 fields
- ✓ Constants: VPC_CIDR, SUBNET_CIDRS, AVAILABILITY_ZONES
- ✓ Properties: is_production, api_subdomain

### Utilities
- ✓ ResourceNamer generates consistent names
- ✓ create_tags merges base + custom tags
- ✓ merge_tags handles multiple dictionaries

### Components
- ✓ 13 component classes defined
- ✓ Each has get_outputs() method
- ✓ Output dataclasses properly typed

### Documentation
- ✓ All modules have docstrings
- ✓ All classes documented
- ✓ All functions documented

## Skipped Tests

1. **test_vpc_component_instantiation** (skipped)
   - Reason: Requires Pulumi runtime context
   - When to run: `pulumi preview` or `pulumi up`

## Before Deployment

1. **Verify Configuration**
   ```bash
   pulumi config get environment
   pulumi config get domain
   ```

2. **Check Credentials**
   ```bash
   aws sts get-caller-identity
   ```

3. **Preview Stack**
   ```bash
   pulumi preview
   ```

4. **Deploy**
   ```bash
   pulumi up
   ```

## Debugging Tests

### Run with Detailed Output
```bash
python -m pytest tests/infrastructure/ -vv --tb=long
```

### Run Single Test
```bash
python -m pytest tests/infrastructure/test_iac_syntax.py::TestIacImports::test_all_components_importable -v
```

### Generate Coverage HTML Report
```bash
python -m pytest tests/infrastructure/ --cov=IAC --cov-report=html
open htmlcov/index.html
```

## Notes

- Tests validate **code structure**, not AWS resource creation
- AWS resource instantiation is covered by Pulumi runtime + `pulumi preview`
- For full validation, use `pulumi preview` with proper AWS credentials
- Component dependency order is: Networking → Security → Storage → Compute → Edge

## Related Files

- Main report: `INFRASTRUCTURE_TEST_REPORT.md`
- Entry point: `IAC/__main__.py`
- Pulumi config: `IAC/Pulumi.yaml`, `IAC/Pulumi.dev.yaml`, `IAC/Pulumi.prod.yaml`
