# Student Helper Infrastructure (IAC)

AWS infrastructure for the Student Helper RAG application, built with **Pulumi** and **Python**.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [Configuration System](#configuration-system)
4. [Component Reference](#component-reference)
5. [Networking Deep Dive](#networking-deep-dive)
6. [Security Patterns](#security-patterns)
7. [Deployment Guide](#deployment-guide)
8. [Environment Matrix](#environment-matrix)
9. [Outputs Reference](#outputs-reference)
10. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### High-Level Architecture

```
                           INTERNET
                               │
            ┌──────────────────┴──────────────────┐
            │                                     │
            ▼                                     ▼
    ┌───────────────┐                    ┌───────────────┐
    │  CloudFront   │                    │  API Gateway  │
    │  (Frontend)   │                    │  (HTTP API)   │
    └───────┬───────┘                    └───────┬───────┘
            │                                    │
            │ OAI                                │ VPC Link
            ▼                                    ▼
┌───────────────────────────────────────────────────────────────┐
│                         VPC (10.0.0.0/16)                     │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    PRIVATE SUBNETS                      │  │
│  │                                                         │  │
│  │   ┌─────────────┐    ┌─────────────┐    ┌───────────┐  │  │
│  │   │    EC2      │    │   Lambda    │    │    RDS    │  │  │
│  │   │  Backend    │───▶│  Processor  │───▶│ PostgreSQL│  │  │
│  │   │  (FastAPI)  │    │             │    │           │  │  │
│  │   └──────┬──────┘    └──────┬──────┘    └───────────┘  │  │
│  │          │                  │                          │  │
│  │          │    VPC Endpoints │                          │  │
│  │          ▼                  ▼                          │  │
│  │   ┌─────────────────────────────────────────────────┐  │  │
│  │   │  S3 (Gateway)  │  SQS  │  Bedrock  │  Secrets   │  │  │
│  │   └─────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
                               │
                               ▼
                        ┌─────────────┐
                        │ AWS Services│
                        │ (Private)   │
                        └─────────────┘
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **No NAT Gateway** | Cost savings; all AWS access via VPC Endpoints |
| **VPC Link** | Private API Gateway integration without public EC2 IP |
| **S3 Vectors** | Native vector storage, no separate vector DB needed |
| **SQS + Lambda** | Async document processing, decoupled from API |
| **Multi-AZ RDS** | Production high availability (configurable per env) |

### Data Flow

```
1. User uploads PDF → API Gateway → EC2 → S3 (documents bucket)
                                       → SQS (processing queue)

2. SQS triggers Lambda → Parse PDF → Chunk → Embed (Bedrock Titan)
                                           → Store vectors (S3 Vectors)
                                           → Update metadata (RDS)

3. User asks question → API Gateway → EC2 → Retrieve vectors (S3 Vectors)
                                          → Generate answer (Bedrock Claude)
                                          → Return with citations
```

---

## Project Structure

```
IAC/
├── __main__.py                 # Orchestrator - deploys all components in order
├── Pulumi.yaml                 # Base Pulumi configuration
├── Pulumi.dev.yaml             # Development environment config
├── Pulumi.prod.yaml            # Production environment config
├── Pulumi.studdy-buddy.yaml    # Local development config
│
├── configs/                    # Configuration system
│   ├── __init__.py
│   ├── base.py                 # EnvironmentConfig dataclass
│   ├── environment.py          # Config loader from Pulumi stack
│   └── constants.py            # Global constants (CIDRs, ports, defaults)
│
├── utils/                      # Utility functions
│   ├── __init__.py
│   ├── naming.py               # ResourceNamer - consistent naming
│   ├── tags.py                 # Tag factory for cost allocation
│   └── outputs.py              # Write outputs to .env file
│
├── components/                 # AWS resource components
│   ├── networking/
│   │   ├── vpc.py              # VPC + Subnets + Route Tables
│   │   ├── security_groups.py  # Security group definitions
│   │   └── vpc_endpoints.py    # Gateway & Interface endpoints
│   │
│   ├── security/
│   │   ├── iam_roles.py        # EC2 & Lambda IAM roles
│   │   └── secrets_manager.py  # API keys & credentials
│   │
│   ├── storage/
│   │   ├── s3_buckets.py       # Documents, Vectors, Frontend
│   │   ├── rds_postgres.py     # PostgreSQL database
│   │   └── ecr_repository.py   # Lambda container registry
│   │
│   ├── messaging/
│   │   └── sqs_queues.py       # Processing queue + DLQ
│   │
│   ├── compute/
│   │   ├── ec2_backend.py      # FastAPI backend instance
│   │   └── lambda_processor.py # Document processor function
│   │
│   └── edge/
│       ├── api_gateway.py      # HTTP API + VPC Link
│       └── cloudfront.py       # CDN for frontend
│
└── diagrams/                   # Generated architecture diagrams
```

### Deployment Order

The `__main__.py` orchestrator deploys resources in 6 layers:

```python
# Layer 1: Networking Foundation
vpc = VpcComponent(...)                    # VPC, subnets, route tables
security_groups = SecurityGroupsComponent(...)  # Firewall rules

# Layer 2: IAM Roles
iam_roles = IamRolesComponent(...)         # EC2 & Lambda permissions

# Layer 3: Secrets, Storage, Messaging
secrets = SecretsManagerComponent(...)     # API keys, DB credentials
s3_buckets = S3BucketsComponent(...)       # Document & vector storage
sqs_queues = SqsQueuesComponent(...)       # Async processing queue

# Layer 4: VPC Endpoints & Database
vpc_endpoints = VpcEndpointsComponent(...) # Private AWS service access
rds = RdsPostgresComponent(...)            # PostgreSQL database

# Layer 5: Compute
ec2_backend = Ec2BackendComponent(...)     # FastAPI backend
lambda_processor = LambdaProcessorComponent(...)  # Doc processor

# Layer 6: Edge Services
cloudfront = CloudFrontComponent(...)      # Frontend CDN
api_gateway = ApiGatewayComponent(...)     # API routing
```

---

## Configuration System

### EnvironmentConfig (configs/base.py)

Type-safe configuration dataclass:

```python
@dataclass
class EnvironmentConfig:
    """Environment-specific configuration."""
    environment: str              # dev, staging, prod
    domain: str                   # Base domain name
    ec2_instance_type: str        # EC2 instance size
    rds_instance_class: str       # RDS instance size
    rds_allocated_storage: int    # Storage in GB
    lambda_memory: int            # Lambda memory in MB
    lambda_timeout: int           # Lambda timeout in seconds
    enable_deletion_protection: bool  # RDS deletion protection
    multi_az: bool                # RDS Multi-AZ deployment

    @property
    def is_production(self) -> bool:
        return self.environment == "prod"

    @property
    def api_subdomain(self) -> str:
        return f"api.{self.domain}"
```

### Constants (configs/constants.py)

```python
# VPC Configuration
VPC_CIDR: Final[str] = "10.0.0.0/16"

# Subnet CIDR blocks
SUBNET_CIDRS: Final[dict[str, str]] = {
    "private": "10.0.1.0/24",   # EC2 Backend
    "lambda": "10.0.2.0/24",    # Lambda Processor
    "data": "10.0.3.0/24",      # RDS PostgreSQL (AZ-a)
    "data_b": "10.0.4.0/24",    # RDS PostgreSQL (AZ-b)
}

# Availability zones
AVAILABILITY_ZONES: Final[list[str]] = [
    "ap-southeast-2a",
    "ap-southeast-2b",
    "ap-southeast-2c",
]

# Port configurations
PORTS: Final[dict[str, int]] = {
    "http": 80,
    "https": 443,
    "fastapi": 8000,
    "postgres": 5432,
}

# SQS defaults
SQS_DEFAULTS: Final[dict[str, int]] = {
    "visibility_timeout_seconds": 360,      # 6 min (Lambda timeout + buffer)
    "message_retention_seconds": 1209600,   # 14 days
    "max_receive_count": 3,                 # Retries before DLQ
}
```

### ResourceNamer (utils/naming.py)

Consistent naming pattern: `{project}-{environment}-{resource}`

```python
class ResourceNamer:
    def __init__(self, project: str, environment: str):
        self.project = project
        self.environment = environment
        self.prefix = f"{project}-{environment}"

    def name(self, resource: str) -> str:
        """Generate resource name: student-helper-dev-backend"""
        if not resource:
            return self.prefix
        return f"{self.prefix}-{resource}"

    def bucket_name(self, suffix: str) -> str:
        """Generate globally unique S3 bucket name."""
        return f"{self.prefix}-{suffix}"

    def secret_name(self, name: str) -> str:
        """Generate Secrets Manager path: student-helper/dev/api-key"""
        return f"{self.project}/{self.environment}/{name}"
```

---

## Component Reference

### VPC Component (networking/vpc.py)

Creates the network foundation with 5 subnets across 2 AZs:

```python
class VpcComponent(pulumi.ComponentResource):
    """VPC with private subnets and route tables."""

    def __init__(self, name: str, environment: str, opts=None):
        # VPC: 10.0.0.0/16 (65,536 IPs)
        self.vpc = aws.ec2.Vpc(
            f"{name}-vpc",
            cidr_block=VPC_CIDR,
            enable_dns_hostnames=True,
            enable_dns_support=True,
        )

        # Subnets distribution:
        # ┌────────────────────────────────────────────┐
        # │           AZ-a              AZ-b           │
        # │  ┌──────────────────┐ ┌──────────────────┐ │
        # │  │ public (NAT)     │ │                  │ │
        # │  │ private (EC2)    │ │                  │ │
        # │  │ lambda           │ │                  │ │
        # │  │ data (RDS)       │ │ data_b (RDS)     │ │
        # │  └──────────────────┘ └──────────────────┘ │
        # └────────────────────────────────────────────┘
```

**Outputs:**
- `vpc_id` - VPC identifier
- `private_subnet_id` - EC2 backend subnet
- `lambda_subnet_id` - Lambda processor subnet
- `data_subnet_id` / `data_subnet_id_b` - RDS subnets (Multi-AZ)
- `private_route_table_id` - Route table for private subnets

### Security Groups Component (networking/security_groups.py)

Defines 4 security groups with least-privilege rules:

```python
# Backend SG: Allows FastAPI traffic from within VPC
self.backend_sg = aws.ec2.SecurityGroup(
    f"{name}-backend-sg",
    vpc_id=vpc_id,
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=PORTS["fastapi"],  # 8000
            to_port=PORTS["fastapi"],
            cidr_blocks=[VPC_CIDR],      # Only from VPC
        ),
    ],
    egress=[ALL_OUTBOUND],
)

# Database SG: Allows PostgreSQL from backend and lambda only
self.database_sg = aws.ec2.SecurityGroup(
    f"{name}-database-sg",
    vpc_id=vpc_id,
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=PORTS["postgres"],  # 5432
            to_port=PORTS["postgres"],
            security_groups=[
                self.backend_sg.id,
                self.lambda_sg.id,
            ],
        ),
    ],
)
```

**Security Group Matrix:**

| SG | Inbound | Source | Purpose |
|----|---------|--------|---------|
| backend-sg | 8000/tcp | VPC CIDR | FastAPI from API Gateway |
| lambda-sg | (none) | - | Outbound only |
| database-sg | 5432/tcp | backend-sg, lambda-sg | PostgreSQL access |
| endpoints-sg | 443/tcp | backend-sg, lambda-sg | VPC Endpoint HTTPS |

### VPC Endpoints Component (networking/vpc_endpoints.py)

Private access to AWS services without internet:

```python
# Gateway Endpoint (FREE) - S3
self.s3_endpoint = aws.ec2.VpcEndpoint(
    f"{name}-s3-endpoint",
    vpc_id=vpc_id,
    service_name=f"com.amazonaws.{region}.s3",
    vpc_endpoint_type="Gateway",
    route_table_ids=route_table_ids,  # Automatic routing
)

# Interface Endpoint (PAID) - SQS with PrivateLink
self.sqs_endpoint = aws.ec2.VpcEndpoint(
    f"{name}-sqs-endpoint",
    vpc_id=vpc_id,
    service_name=f"com.amazonaws.{region}.sqs",
    vpc_endpoint_type="Interface",
    subnet_ids=subnet_ids,
    security_group_ids=[security_group_id],
    private_dns_enabled=True,  # DNS hijacking
)
```

**Endpoint Types:**

| Type | Services | Cost | How it Works |
|------|----------|------|--------------|
| Gateway | S3, DynamoDB | Free | Route table entry |
| Interface | SQS, Secrets, Bedrock, ECR | ~$0.01/hr + data | ENI in subnet with private DNS |

### IAM Roles Component (security/iam_roles.py)

Least-privilege permissions for compute resources:

```python
# EC2 Role Permissions
ec2_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
            "Resource": "arn:aws:s3:::student-helper-*/*"
        },
        {
            "Effect": "Allow",
            "Action": ["sqs:SendMessage", "sqs:ReceiveMessage"],
            "Resource": "arn:aws:sqs:*:*:student-helper-*"
        },
        {
            "Effect": "Allow",
            "Action": ["bedrock:InvokeModel"],
            "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
        },
    ]
}

# Lambda Role Permissions (includes VPC access)
lambda_managed_policies = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole",
]
```

### S3 Buckets Component (storage/s3_buckets.py)

Three buckets for different data types:

```python
# Documents bucket - PDF storage with versioning
self.documents_bucket = aws.s3.BucketV2(
    f"{name}-documents",
    bucket=namer.bucket_name("documents"),
)
aws.s3.BucketVersioningV2(
    f"{name}-documents-versioning",
    bucket=self.documents_bucket.id,
    versioning_configuration={"status": "Enabled"},
)

# Vectors bucket - S3 Vectors for embeddings
self.vectors_bucket = aws_native.s3.Bucket(
    f"{name}-vectors",
    bucket_name=namer.bucket_name("vectors"),
)

# S3 Vector Index
self.vectors_index = aws_native.s3vectors.Index(
    f"{name}-vectors-index",
    bucket_name=self.vectors_bucket.bucket_name,
    index_name="documents",
    dimension=1536,  # Titan v2 embedding dimension
    distance_metric="COSINE",
    metadata=[
        {"name": "document_id", "data_type": "STRING", "filterable": True},
        {"name": "session_id", "data_type": "STRING", "filterable": True},
        {"name": "page_number", "data_type": "NUMBER", "filterable": True},
        {"name": "text_content", "data_type": "STRING", "filterable": False},
    ],
)
```

### RDS PostgreSQL Component (storage/rds_postgres.py)

PostgreSQL database with environment-aware configuration:

```python
class RdsPostgresComponent(pulumi.ComponentResource):
    def __init__(self, name, environment, config, subnet_ids, security_group_id):
        # Subnet group spans 2 AZs (AWS requirement)
        self.subnet_group = aws.rds.SubnetGroup(
            f"{name}-subnet-group",
            subnet_ids=subnet_ids,  # [data_subnet, data_subnet_b]
        )

        self.instance = aws.rds.Instance(
            f"{name}-postgres",
            engine="postgres",
            engine_version="16",
            instance_class=config.rds_instance_class,
            allocated_storage=config.rds_allocated_storage,
            storage_type="gp3",
            storage_encrypted=True,
            db_name="studenthelper",
            username="postgres",
            manage_master_user_password=True,  # AWS manages in Secrets Manager
            db_subnet_group_name=self.subnet_group.name,
            vpc_security_group_ids=[security_group_id],
            multi_az=config.multi_az,
            deletion_protection=config.enable_deletion_protection,
            backup_retention_period=7 if config.is_production else 1,
        )
```

### SQS Queues Component (messaging/sqs_queues.py)

Message queue with dead-letter queue for failed processing:

```python
# Dead Letter Queue - failed messages go here
self.dlq = aws.sqs.Queue(
    f"{name}-dlq",
    message_retention_seconds=SQS_DEFAULTS["message_retention_seconds"],
)

# Main processing queue
self.queue = aws.sqs.Queue(
    f"{name}-doc-processor",
    visibility_timeout_seconds=SQS_DEFAULTS["visibility_timeout_seconds"],
    message_retention_seconds=SQS_DEFAULTS["message_retention_seconds"],
    redrive_policy=self.dlq.arn.apply(lambda arn: json.dumps({
        "deadLetterTargetArn": arn,
        "maxReceiveCount": SQS_DEFAULTS["max_receive_count"],
    })),
)
```

**Queue Flow:**
```
Upload → SQS Queue ──┬──► Lambda (success) → Delete message
                     │
                     └──► Lambda (fail x3) → DLQ (for inspection)
```

### EC2 Backend Component (compute/ec2_backend.py)

FastAPI backend with user data bootstrap:

```python
class Ec2BackendComponent(pulumi.ComponentResource):
    def __init__(self, name, environment, config, subnet_id, security_group_id, instance_profile_name):
        # Ubuntu 24.04 LTS AMI
        ami = aws.ec2.get_ami(
            most_recent=True,
            owners=["099720109477"],  # Canonical
            filters=[
                {"name": "name", "values": ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]},
            ],
        )

        # User data script - bootstraps the instance
        user_data = f"""#!/bin/bash
set -e
apt-get update && apt-get install -y python3.12 python3-pip
pip3 install uvicorn fastapi

# Create systemd service for FastAPI
cat > /etc/systemd/system/fastapi.service << 'EOF'
[Unit]
Description=FastAPI Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/app
ExecStart=/usr/bin/python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable fastapi
"""

        self.instance = aws.ec2.Instance(
            f"{name}",
            ami=ami.id,
            instance_type=config.ec2_instance_type,
            subnet_id=subnet_id,
            vpc_security_group_ids=[security_group_id],
            iam_instance_profile=instance_profile_name,
            user_data=user_data,
            root_block_device=aws.ec2.InstanceRootBlockDeviceArgs(
                volume_size=20,
                volume_type="gp3",
                encrypted=True,
            ),
            metadata_options=aws.ec2.InstanceMetadataOptionsArgs(
                http_tokens="required",  # IMDSv2 enforced
            ),
        )
```

### Lambda Processor Component (compute/lambda_processor.py)

Document processing with SQS trigger:

```python
class LambdaProcessorComponent(pulumi.ComponentResource):
    def __init__(self, name, environment, config, role_arn, subnet_ids,
                 security_group_id, sqs_queue_arn, documents_bucket_name,
                 vectors_bucket_name, secrets_arn):

        self.function = aws.lambda_.Function(
            f"{name}",
            role=role_arn,
            package_type="Image",
            image_uri=f"{ecr_repo}:latest",
            memory_size=config.lambda_memory,
            timeout=config.lambda_timeout,
            vpc_config=aws.lambda_.FunctionVpcConfigArgs(
                subnet_ids=subnet_ids,
                security_group_ids=[security_group_id],
            ),
            environment=aws.lambda_.FunctionEnvironmentArgs(
                variables={
                    "ENVIRONMENT": environment,
                    "DOCUMENTS_BUCKET": documents_bucket_name,
                    "VECTORS_BUCKET": vectors_bucket_name,
                    "SECRETS_ARN": secrets_arn,
                },
            ),
        )

        # SQS Trigger - processes one message at a time
        self.event_source = aws.lambda_.EventSourceMapping(
            f"{name}-sqs-trigger",
            event_source_arn=sqs_queue_arn,
            function_name=self.function.name,
            batch_size=1,  # One document per invocation
        )
```

### API Gateway Component (edge/api_gateway.py)

HTTP API with VPC Link for private EC2 access:

```python
class ApiGatewayComponent(pulumi.ComponentResource):
    def __init__(self, name, environment, vpc_id, subnet_ids,
                 security_group_id, ec2_private_ip):

        # VPC Link - bridge from API Gateway to private VPC
        self.vpc_link = aws.apigatewayv2.VpcLink(
            f"{name}-vpc-link",
            subnet_ids=subnet_ids,
            security_group_ids=[security_group_id],
        )

        # HTTP API
        self.api = aws.apigatewayv2.Api(
            f"{name}-api",
            protocol_type="HTTP",
            cors_configuration=aws.apigatewayv2.ApiCorsConfigurationArgs(
                allow_origins=["*"],
                allow_methods=["*"],
                allow_headers=["*"],
            ),
        )

        # Integration - proxy to EC2 via VPC Link
        self.integration = aws.apigatewayv2.Integration(
            f"{name}-integration",
            api_id=self.api.id,
            integration_type="HTTP_PROXY",
            integration_method="ANY",
            integration_uri=ec2_private_ip.apply(
                lambda ip: f"http://{ip}:8000/{{proxy}}"
            ),
            connection_type="VPC_LINK",
            connection_id=self.vpc_link.id,
        )

        # Catch-all route
        self.route = aws.apigatewayv2.Route(
            f"{name}-route",
            api_id=self.api.id,
            route_key="ANY /{proxy+}",
            target=self.integration.id.apply(lambda id: f"integrations/{id}"),
        )
```

### CloudFront Component (edge/cloudfront.py)

CDN for frontend with S3 origin:

```python
class CloudFrontComponent(pulumi.ComponentResource):
    def __init__(self, name, environment, frontend_bucket_name,
                 frontend_bucket_arn, frontend_bucket_domain):

        # Origin Access Identity - secure S3 access
        self.oai = aws.cloudfront.OriginAccessIdentity(
            f"{name}-oai",
            comment=f"OAI for {name} frontend",
        )

        self.distribution = aws.cloudfront.Distribution(
            f"{name}-distribution",
            enabled=True,
            default_root_object="index.html",
            origins=[
                aws.cloudfront.DistributionOriginArgs(
                    domain_name=frontend_bucket_domain,
                    origin_id="S3Origin",
                    s3_origin_config=aws.cloudfront.DistributionOriginS3OriginConfigArgs(
                        origin_access_identity=self.oai.cloudfront_access_identity_path,
                    ),
                ),
            ],
            default_cache_behavior=aws.cloudfront.DistributionDefaultCacheBehaviorArgs(
                allowed_methods=["GET", "HEAD"],
                cached_methods=["GET", "HEAD"],
                target_origin_id="S3Origin",
                viewer_protocol_policy="redirect-to-https",
                compress=True,
            ),
            # SPA routing - 404/403 → index.html
            custom_error_responses=[
                aws.cloudfront.DistributionCustomErrorResponseArgs(
                    error_code=404,
                    response_code=200,
                    response_page_path="/index.html",
                ),
                aws.cloudfront.DistributionCustomErrorResponseArgs(
                    error_code=403,
                    response_code=200,
                    response_page_path="/index.html",
                ),
            ],
            price_class="PriceClass_100",  # US, Canada, Europe
        )
```

---

## Networking Deep Dive

### Subnet Architecture

```
VPC: 10.0.0.0/16 (65,536 available IPs)
│
├── Public Subnet: 10.0.0.0/24 (AZ-a)
│   └── [Reserved for NAT Gateway if needed]
│
├── Private Subnet: 10.0.1.0/24 (AZ-a)
│   └── EC2 Backend (FastAPI)
│
├── Lambda Subnet: 10.0.2.0/24 (AZ-b)
│   ├── Lambda ENIs
│   └── VPC Endpoint ENIs
│
├── Data Subnet: 10.0.3.0/24 (AZ-a)
│   └── RDS Primary
│
└── Data Subnet B: 10.0.4.0/24 (AZ-b)
    └── RDS Standby (Multi-AZ)
```

### Why No NAT Gateway?

Traditional architecture:
```
Lambda → NAT Gateway → Internet Gateway → AWS Services
         ($0.045/hr)   (data charges)
```

This architecture:
```
Lambda → VPC Endpoint → AWS Services
         ($0.01/hr)    (lower data charges, private)
```

**Benefits:**
- ~75% cost reduction on gateway charges
- All traffic stays on AWS backbone (lower latency)
- No internet exposure (better security)

### VPC Endpoints Explained

**Gateway Endpoint (S3):**
```
┌─────────────────────────────────────────┐
│ Route Table                             │
│ ┌─────────────────────────────────────┐ │
│ │ 10.0.0.0/16 → local                 │ │
│ │ pl-xxx (S3) → vpce-xxx              │ │  ← Added by Gateway Endpoint
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

**Interface Endpoint (SQS, Bedrock):**
```
┌─────────────────────────────────────────┐
│ Lambda Subnet                           │
│ ┌─────────────────────────────────────┐ │
│ │ ENI: 10.0.2.50 (SQS Endpoint)       │ │  ← PrivateLink ENI
│ │ ENI: 10.0.2.51 (Bedrock Endpoint)   │ │
│ │ ENI: 10.0.2.52 (Lambda)             │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘

Private DNS hijacking:
  sqs.ap-southeast-2.amazonaws.com → 10.0.2.50 (private)
  Instead of → 52.xx.xx.xx (public)
```

### VPC Link vs VPC Endpoint

| | VPC Endpoint | VPC Link |
|---|--------------|----------|
| **Direction** | Outbound (VPC → AWS) | Inbound (API GW → VPC) |
| **Use Case** | Lambda calling S3 | Users calling EC2 |
| **Creates** | Route entry or ENI | ENI in subnet |
| **DNS** | Hijacks AWS service DNS | N/A |

```
                    INTERNET
                        │
                        ▼
              ┌─────────────────┐
              │   API Gateway   │
              └────────┬────────┘
                       │ VPC Link (inbound)
                       ▼
┌──────────────────────────────────────────────┐
│                    VPC                        │
│                                              │
│   ┌──────────┐                               │
│   │   EC2    │                               │
│   └────┬─────┘                               │
│        │                                     │
│        │ VPC Endpoint (outbound)             │
│        ▼                                     │
│   ┌──────────┐                               │
│   │ S3, SQS  │ (via PrivateLink)            │
│   └──────────┘                               │
└──────────────────────────────────────────────┘
```

---

## Security Patterns

### Defense in Depth

```
Layer 1: Edge Security
├── CloudFront: DDoS protection, HTTPS only
└── API Gateway: Rate limiting, CORS

Layer 2: Network Security
├── VPC: Isolated network
├── Private Subnets: No public IPs
├── Security Groups: Port-level firewall
└── VPC Endpoints: No internet exposure

Layer 3: Identity Security
├── IAM Roles: Least-privilege permissions
├── Instance Profile: No hardcoded credentials
└── Secrets Manager: Encrypted secrets

Layer 4: Data Security
├── S3: AES-256 encryption at rest
├── RDS: AES-256 encryption at rest
├── TLS: Encryption in transit
└── IMDSv2: SSRF protection
```

### Security Group Rules

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Group Flow                       │
│                                                             │
│  Internet → API Gateway → VPC Link                          │
│                              │                              │
│                              ▼                              │
│                    ┌─────────────────┐                      │
│                    │   backend-sg    │                      │
│                    │  IN: 8000/tcp   │ ← from VPC CIDR      │
│                    └────────┬────────┘                      │
│                             │                               │
│              ┌──────────────┼──────────────┐               │
│              ▼              ▼              ▼               │
│     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│     │ database-sg │ │ endpoints-sg│ │  lambda-sg  │        │
│     │IN: 5432/tcp │ │IN: 443/tcp  │ │ OUT only    │        │
│     └─────────────┘ └─────────────┘ └─────────────┘        │
│           ▲              ▲                                  │
│           │              │                                  │
│           └──────────────┴── from backend-sg, lambda-sg     │
└─────────────────────────────────────────────────────────────┘
```

### IAM Permissions Matrix

| Resource | S3 | SQS | Secrets | Bedrock | RDS |
|----------|----|----|---------|---------|-----|
| EC2 | Read/Write | Send/Receive | Read | Claude | Via SG |
| Lambda | Read/Write + Vectors | Receive/Delete | Read | Titan | Via SG |

### Encryption

| Resource | At Rest | In Transit | Key Management |
|----------|---------|------------|----------------|
| S3 | AES-256 | TLS 1.2+ | AWS Managed |
| RDS | AES-256 | TLS 1.2+ | AWS Managed |
| Secrets Manager | AES-256 | TLS 1.2+ | AWS Managed |
| ECR | AES-256 | TLS 1.2+ | AWS Managed |

---

## Deployment Guide

### Prerequisites

```powershell
# Install Pulumi
winget install Pulumi.Pulumi

# Install AWS CLI and configure
aws configure

# Install Python dependencies
cd Student_Helper
uv sync
```

### Deploy Development Environment

```powershell
cd IAC

# Select/create dev stack
pulumi stack select dev --create

# Set required configuration
pulumi config set student-helper-infra:environment dev
pulumi config set student-helper-infra:domain dev.studenthelper.com

# Preview changes
pulumi preview

# Deploy
pulumi up
```

### Deploy Production Environment

```powershell
cd IAC

# Select/create prod stack
pulumi stack select prod --create

# Set production configuration
pulumi config set student-helper-infra:environment prod
pulumi config set student-helper-infra:domain studenthelper.com
pulumi config set student-helper-infra:rds_instance_class db.t3.medium
pulumi config set student-helper-infra:multi_az true
pulumi config set student-helper-infra:enable_deletion_protection true

# Deploy
pulumi up
```

### Post-Deployment Steps

1. **Populate Secrets:**
```powershell
aws secretsmanager put-secret-value \
    --secret-id student-helper/dev/google-api-key \
    --secret-string "your-google-api-key"

aws secretsmanager put-secret-value \
    --secret-id student-helper/dev/anthropic-api-key \
    --secret-string "your-anthropic-api-key"
```

2. **Deploy Lambda Code:**
```powershell
# Build and push Docker image
docker build -t student-helper-processor .
docker tag student-helper-processor:latest <ecr-repo>:latest
docker push <ecr-repo>:latest

# Update Lambda to use new image
aws lambda update-function-code \
    --function-name student-helper-dev-doc-processor \
    --image-uri <ecr-repo>:latest
```

3. **Deploy Frontend:**
```powershell
# Use the deployment script
cd study-buddy-ai
.\deploy.ps1

# Or with cache invalidation
.\deploy.ps1 -InvalidateCache -DistributionId "YOUR_DISTRIBUTION_ID"
```

4. **Deploy Backend to ECR:**
```powershell
# Use the deployment script
cd backend
.\deploy-ecr.ps1

# This will:
# - Create ECR repo if needed
# - Build Docker image
# - Push to ECR
```

5. **Deploy Backend to EC2:**
```powershell
# Connect via SSM
aws ssm start-session --target i-045c7f914f0447290 --region ap-southeast-2

# Run the setup script on EC2
bash ec2-setup.sh
```

### Destroy Environment

```powershell
# Remove deletion protection first (production)
pulumi config set student-helper-infra:enable_deletion_protection false
pulumi up

# Destroy all resources
pulumi destroy
```

---

## Environment Matrix

| Setting | Dev | Staging | Prod |
|---------|-----|---------|------|
| **EC2 Instance** | t3.micro | t3.small | t3.small |
| **RDS Instance** | db.t3.micro | db.t3.small | db.t3.medium |
| **RDS Storage** | 20 GB | 30 GB | 50 GB |
| **RDS Multi-AZ** | No | No | Yes |
| **Lambda Memory** | 512 MB | 512 MB | 1024 MB |
| **Lambda Timeout** | 300s | 300s | 300s |
| **Deletion Protection** | No | No | Yes |
| **Backup Retention** | 1 day | 7 days | 7 days |
| **Domain** | dev.studenthelper.com | staging.studenthelper.com | studenthelper.com |

### Estimated Costs (Monthly)

| Resource | Dev | Prod |
|----------|-----|------|
| EC2 (t3.micro/small) | ~$8 | ~$15 |
| RDS (db.t3.micro/medium) | ~$15 | ~$50 |
| RDS Storage | ~$2 | ~$6 |
| VPC Endpoints (4x Interface) | ~$30 | ~$30 |
| S3 + Data Transfer | ~$5 | ~$20 |
| Lambda | ~$1 | ~$5 |
| CloudFront | ~$1 | ~$10 |
| API Gateway | ~$1 | ~$5 |
| **Total** | **~$63** | **~$141** |

---

## Outputs Reference

After deployment, outputs are:
1. Exported to Pulumi stack state
2. Written to `infrastructure.env` file

### Available Outputs

| Output | Description | Example |
|--------|-------------|---------|
| `vpc_id` | VPC identifier | vpc-0abc123def456 |
| `ec2_instance_id` | Backend EC2 instance | i-0abc123def456 |
| `ec2_private_ip` | EC2 private IP | 10.0.1.50 |
| `lambda_function_name` | Lambda function name | student-helper-dev-doc-processor |
| `lambda_ecr_repository` | ECR repository URL | 123456789.dkr.ecr.ap-southeast-2.amazonaws.com/student-helper-dev-processor |
| `rds_endpoint` | PostgreSQL endpoint | student-helper-dev-postgres.xxx.ap-southeast-2.rds.amazonaws.com:5432 |
| `documents_bucket` | PDF storage bucket | student-helper-dev-documents |
| `vectors_bucket` | Vector storage bucket | student-helper-dev-vectors |
| `vectors_index` | Vector index name | documents |
| `frontend_bucket` | Frontend assets bucket | student-helper-dev-frontend |
| `sqs_queue_url` | Processing queue URL | https://sqs.ap-southeast-2.amazonaws.com/123456789/student-helper-dev-doc-processor |
| `api_endpoint` | API Gateway endpoint | https://abc123.execute-api.ap-southeast-2.amazonaws.com |
| `cloudfront_domain` | CDN domain | d1234abcdef.cloudfront.net |

### Using Outputs in Application

```python
# Load from infrastructure.env
from dotenv import load_dotenv
import os

load_dotenv("infrastructure.env")

RDS_ENDPOINT = os.getenv("RDS_ENDPOINT")
DOCUMENTS_BUCKET = os.getenv("DOCUMENTS_BUCKET")
API_ENDPOINT = os.getenv("API_ENDPOINT")
```

### Query Outputs via CLI

```powershell
# Get all outputs
pulumi stack output

# Get specific output
pulumi stack output api_endpoint

# Get outputs as JSON
pulumi stack output --json
```

---

## Troubleshooting

### Common Issues

#### RDS Subnet Group Error
```
DBSubnetGroupDoesNotCoverEnoughAZs: The DB subnet group doesn't meet
Availability Zone (AZ) coverage requirement.
```
**Solution:** Ensure subnet group includes subnets in at least 2 AZs. Check that `data_subnet` and `data_subnet_b` are in different AZs.

#### Lambda VPC Timeout
```
Task timed out after 300 seconds
```
**Solution:** Ensure VPC Endpoints exist for all AWS services Lambda needs (S3, SQS, Secrets Manager, Bedrock). Check security group allows outbound HTTPS.

#### EC2 Cannot Reach RDS
**Solution:** Check that `database_sg` allows inbound 5432 from `backend_sg`. Verify both are in the same VPC.

#### API Gateway 502 Bad Gateway
**Solution:**
1. Check EC2 is running and FastAPI is listening on port 8000
2. Verify VPC Link is healthy
3. Check `backend_sg` allows inbound 8000 from VPC CIDR

#### Pulumi State Lock
```
error: the stack is currently locked by another update
```
**Solution:**
```powershell
pulumi cancel  # Cancel stuck operation
# Or force unlock (use with caution)
pulumi stack export | pulumi stack import
```

### Debug Commands

```powershell
# Check EC2 status
aws ec2 describe-instances --filters "Name=tag:Name,Values=*backend*"

# Check RDS status
aws rds describe-db-instances --db-instance-identifier student-helper-dev-postgres

# Check Lambda logs
aws logs tail /aws/lambda/student-helper-dev-doc-processor --follow

# Check SQS queue depth
aws sqs get-queue-attributes \
    --queue-url <queue-url> \
    --attribute-names ApproximateNumberOfMessages

# Test VPC Endpoint connectivity (from EC2)
aws s3 ls --endpoint-url https://s3.ap-southeast-2.amazonaws.com
```

---

## Architecture Decisions Record

| Decision | Options Considered | Choice | Rationale |
|----------|-------------------|--------|-----------|
| IaC Tool | Terraform, CDK, Pulumi | Pulumi | Python native, strong typing, component model |
| API Gateway | REST API, HTTP API | HTTP API | Lower cost, simpler, sufficient for this use case |
| Vector DB | Pinecone, Weaviate, S3 Vectors | S3 Vectors | Native AWS, no separate service, cost effective |
| Compute | ECS, Lambda, EC2 | EC2 + Lambda | EC2 for API (always-on), Lambda for processing (event-driven) |
| NAT | NAT Gateway, NAT Instance, VPC Endpoints | VPC Endpoints | Cost savings, better security |
| RDS Auth | Password, IAM Auth | AWS-managed password | Simpler, auto-rotation via Secrets Manager |

---

## Contributing

1. Create feature branch from `master`
2. Make changes in `IAC/` directory
3. Run `pulumi preview` to validate
4. Submit PR with infrastructure changes

### Adding New Components

1. Create component class in appropriate `components/` subdirectory
2. Follow existing patterns (ComponentResource, dataclass outputs)
3. Add to `__main__.py` orchestrator in correct layer
4. Update this README with component documentation

---

## References

- [Pulumi AWS Provider](https://www.pulumi.com/registry/packages/aws/)
- [AWS VPC Documentation](https://docs.aws.amazon.com/vpc/)
- [S3 Vectors Documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-express-one-zone.html)
- [API Gateway VPC Links](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-vpc-links.html)
