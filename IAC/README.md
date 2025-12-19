# 🏗 Student Helper Infrastructure as Code (IAC)

> **Educational Documentation** for deploying and understanding the Student Helper cloud architecture.

This document provides both a quick reference and links to detailed educational resources for the Student Helper infrastructure. Built with **Pulumi** + **Python** targeting **AWS ap-southeast-2 (Sydney)**.

---

## 📚 Documentation Index

| Document                                                                                       | Purpose                                                              |
| ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **This README**                                                                                | Quick reference and architecture overview                            |
| **[diagrams/ARCHITECTS_DEPLOYMENT_CHECKLIST.md](diagrams/ARCHITECTS_DEPLOYMENT_CHECKLIST.md)** | 🎓 **New to Architecture?** Step-by-step learning & validation guide |
| **[diagrams/NETWORKING_DEEP_DIVE.md](diagrams/NETWORKING_DEEP_DIVE.md)**                       | 🔌 Protocol flows, security zones, troubleshooting                   |
| **[diagrams/IAC_COMPREHENSIVE_GUIDE.md](diagrams/IAC_COMPREHENSIVE_GUIDE.md)**                 | 📝 Complete IAC code walkthrough with patterns explained             |

---

## 🎯 Architecture at a Glance

```mermaid
flowchart TB
    subgraph Internet["🌐 INTERNET (Public Users)"]
        User((👤 User<br/>Browser))
    end

    subgraph Edge["☁️ AWS EDGE NETWORK"]
        subgraph CloudFront["CloudFront CDN<br/>d1234.cloudfront.net"]
            CF_TLS["🔒 TLS Termination"]
            CF_Cache["📦 Edge Caching"]
        end

        subgraph Behaviors["📋 Routing Behaviors"]
            B_Static["/static/* → S3"]
            B_API["/api/* → ALB"]
            B_WS["/ws/* → ALB<br/>🔌 WebSocket Headers"]
        end
    end

    subgraph VPC["🏢 VPC: 10.0.0.0/16"]
        subgraph PublicSubnet["🟢 PUBLIC SUBNET (10.0.0.0/24)<br/>ap-southeast-2a"]
            ALB["⚖️ Application Load Balancer<br/>HTTP :80 → Target :8000<br/>Idle: 600s | Sticky: ✅"]
        end

        subgraph PrivateSubnet["🔵 PRIVATE SUBNET (10.0.1.0/24)<br/>ap-southeast-2a"]
            EC2["💻 EC2 Backend (t3.small)<br/>FastAPI + Uvicorn :8000<br/>No Public IP | IAM Profile"]
        end

        subgraph DataSubnet["💾 DATA SUBNET (10.0.3-4.0/24)<br/>Multi-AZ"]
            RDS[("🗄️ RDS PostgreSQL<br/>PostgreSQL 16<br/>Encrypted | Multi-AZ")]
        end

        subgraph LambdaSubnet["λ LAMBDA SUBNET (10.0.2.0/24)<br/>ap-southeast-2b"]
            Lambda["λ Lambda Processor<br/>Document Processing"]
            VPCEndpoints["🔗 VPC Endpoints<br/>S3 | Bedrock | SQS"]
            VPCLink["🔗 VPC Link ENI<br/>API Gateway Tunnel"]
        end

        subgraph Storage["📁 S3 STORAGE"]
            S3Front["📄 S3 Frontend<br/>React SPA"]
            S3Docs["📑 S3 Documents<br/>PDF Uploads"]
            S3Vec["🧮 S3 Vectors<br/>1536-dim Embeddings"]
        end

        subgraph Messaging["📬 MESSAGING"]
            SQS["📬 SQS Queue<br/>Doc Processing"]
            DLQ["⚠️ Dead Letter Queue"]
        end
    end

    subgraph External["☁️ AWS SERVICES (via VPC Endpoints)"]
        Bedrock["🤖 Bedrock AI<br/>Claude | Titan"]
        Secrets["🔐 Secrets Manager"]
    end

    %% User Flow
    User -->|"HTTPS/WSS<br/>TLS 1.2+"| CF_TLS
    CF_TLS --> CF_Cache
    CF_Cache --> Behaviors

    %% CloudFront Routing
    B_Static -->|"OAI"| S3Front
    B_API -->|"HTTP/1.1"| ALB
    B_WS -->|"HTTP/1.1<br/>Upgrade Headers"| ALB

    %% ALB to Backend
    ALB -->|"TCP 8000"| EC2

    %% EC2 Connections
    EC2 -->|"TCP 5432"| RDS
    EC2 -->|"PUT/GET"| S3Docs
    EC2 -->|"Query"| S3Vec
    EC2 -->|"SendMessage"| SQS
    EC2 -.->|"HTTPS 443"| VPCEndpoints
    VPCEndpoints --> Bedrock
    VPCEndpoints --> Secrets

    %% Lambda Processing
    SQS -->|"Event Trigger"| Lambda
    SQS -->|"3 Failures"| DLQ
    Lambda -->|"GET Docs"| S3Docs
    Lambda -->|"PUT Vectors"| S3Vec
    Lambda -->|"UPDATE"| RDS
    Lambda -.-> VPCEndpoints

    %% Styling
    style User fill:#E8EAED,stroke:#5F6368,stroke-width:2px
    style CF_TLS fill:#FF9900,stroke:#CC7700,stroke-width:2px
    style CF_Cache fill:#FF9900,stroke:#CC7700,stroke-width:2px
    style B_WS fill:#FFD699,stroke:#CC7700,stroke-width:2px
    style ALB fill:#FF9900,stroke:#CC7700,stroke-width:2px
    style EC2 fill:#1B73E8,stroke:#0D47A1,stroke-width:2px,color:#fff
    style Lambda fill:#1B73E8,stroke:#0D47A1,stroke-width:2px,color:#fff
    style RDS fill:#4285F4,stroke:#1B66C7,stroke-width:2px,color:#fff
    style S3Front fill:#569A31,stroke:#3D6B22,stroke-width:2px,color:#fff
    style S3Docs fill:#569A31,stroke:#3D6B22,stroke-width:2px,color:#fff
    style S3Vec fill:#34A853,stroke:#1E8E3E,stroke-width:2px,color:#fff
    style SQS fill:#EA4335,stroke:#B71C1C,stroke-width:2px,color:#fff
    style DLQ fill:#EA4335,stroke:#B71C1C,stroke-width:2px,color:#fff
    style Bedrock fill:#FF9900,stroke:#CC7700,stroke-width:2px
    style Secrets fill:#FBBC04,stroke:#E37400,stroke-width:2px
    style VPCEndpoints fill:#34A853,stroke:#1E8E3E,stroke-width:2px,color:#fff
```

---

## 🕐 "The Clock" Connection: Why It Matters

### The Problem We Solved

Previously, WebSocket connections failed with **1006 Abnormal Closure** errors because:

```
❌ Old Path: User → API Gateway (WebSocket API) → VPC Link → ALB → EC2
   Problem: API Gateway WebSocket uses webhook-style callbacks ($connect/$disconnect)
            Your FastAPI expects raw RFC 6455 WebSocket protocol
            Result: Protocol mismatch, immediate disconnection
```

### The Solution

```
✅ New Path: User → CloudFront → ALB → EC2
   Solution: CloudFront passes through Upgrade headers untouched
             ALB maintains HTTP/1.1 for WebSocket upgrade
             EC2 receives actual WebSocket handshake
             Result: Real-time streaming works!
```

> 📖 **For detailed protocol flows and troubleshooting, see [NETWORKING_DEEP_DIVE.md](diagrams/NETWORKING_DEEP_DIVE.md)**

---

## 🔌 Network Component Map

### Layer 1: Edge (Public Internet)

| Component       | Configuration               | Purpose                              |
| --------------- | --------------------------- | ------------------------------------ |
| **CloudFront**  | d1234.cloudfront.net        | Global CDN, TLS termination, routing |
| **S3 Frontend** | student-helper-dev-frontend | Static React SPA assets              |

### Layer 2: Compute (Private VPC)

| Component  | Configuration            | Purpose                       |
| ---------- | ------------------------ | ----------------------------- |
| **ALB**    | Internet-facing, port 80 | Load balancing, health checks |
| **EC2**    | t3.small, port 8000      | FastAPI + Uvicorn             |
| **Lambda** | 512MB-1GB, VPC-enabled   | Async document processing     |

### Layer 3: Data (Isolated)

| Component        | Configuration            | Purpose                  |
| ---------------- | ------------------------ | ------------------------ |
| **RDS**          | PostgreSQL 16, encrypted | Sessions, jobs, metadata |
| **S3 Documents** | Versioned, encrypted     | PDF uploads              |
| **S3 Vectors**   | 1536-dim, cosine metric  | Vector embeddings        |

---

## 🛡️ Security Group Chain

```mermaid
flowchart LR
    subgraph Internet
        CF[☁️ CloudFront<br/>Prefix List]
    end

    subgraph ALB_SG["ALB Security Group"]
        ALB_IN["✅ Inbound: 80<br/>from CloudFront"]
    end

    subgraph Backend_SG["Backend Security Group"]
        BE_IN["✅ Inbound: 8000<br/>from ALB SG"]
    end

    subgraph Database_SG["Database Security Group"]
        DB_IN["✅ Inbound: 5432<br/>from Backend SG<br/>from Lambda SG"]
    end

    CF -->|HTTP 80| ALB_IN
    ALB_IN -->|TCP 8000| BE_IN
    BE_IN -->|TCP 5432| DB_IN
```

**Key Security Features:**

- 🔒 **CloudFront Prefix List**: ALB only accepts traffic from CloudFront edge IPs
- 🔒 **Security Group References**: Rules reference SG IDs, not IP addresses (auto-updates)
- 🔒 **No Public IPs**: EC2 and RDS have no direct internet access
- 🔒 **VPC Endpoints**: AWS services accessed over private network

---

## 🧠 Core Concepts Quick Reference

> These concepts are documented in detail in each module's docstring. This is a quick reference.

### Networking Fundamentals

| Concept                               | What It Does                                                                   |
| ------------------------------------- | ------------------------------------------------------------------------------ |
| **Local Route (10.0.0.0/16 → local)** | Automatic VPC route. All subnets can talk to each other without configuration. |
| **0.0.0.0/0 → IGW**                   | "Send everything else to the internet." Enables bidirectional internet access. |
| **Route Table Association**           | Links a subnet to a route table. Without it, the subnet uses the default.      |

### VPC Link vs VPC Endpoint (Common Confusion!)

| Component        | Direction            | Purpose                                                                         |
| ---------------- | -------------------- | ------------------------------------------------------------------------------- |
| **VPC Endpoint** | OUTBOUND (VPC → AWS) | Lets your private EC2/Lambda reach AWS services (S3, Bedrock) without internet. |
| **VPC Link**     | INBOUND (AWS → VPC)  | Lets API Gateway (a public AWS service) tunnel INTO your private VPC.           |

### Security Groups

| Concept                  | Meaning                                                                      |
| ------------------------ | ---------------------------------------------------------------------------- |
| **Stateful**             | Allow inbound → reply automatically allowed outbound (no extra rule needed). |
| **Identity-based rules** | `referenced_security_group_id` = allow by "badge", not by IP.                |
| **Default stance**       | Inbound: DENY ALL. Outbound: ALLOW ALL.                                      |

### ALB Chain

| Resource          | Analogy                | Purpose                                          |
| ----------------- | ---------------------- | ------------------------------------------------ |
| **Load Balancer** | The building           | Has a DNS name, receives all traffic             |
| **Listener**      | The door (port 80/443) | Binds to a port, defines what to do with traffic |
| **Target Group**  | The employee pool      | Healthy EC2 instances to forward to              |

### CloudFront Strategy

| Path          | Destination | Caching                                  |
| ------------- | ----------- | ---------------------------------------- |
| `/` (default) | S3 Frontend | ✅ Cached globally                       |
| `/api/*`      | ALB Backend | ❌ No cache                              |
| `/ws/*`       | ALB Backend | ❌ No cache, WebSocket headers forwarded |

> 📖 **For detailed explanations, read the docstrings in each component file.**

## 📊 Complete Request Flow Diagrams

### Static Asset Request

```mermaid
sequenceDiagram
    participant Browser
    participant CF as CloudFront
    participant S3 as S3 Frontend

    Browser->>CF: GET /index.html
    alt Cache HIT
        CF-->>Browser: 200 OK (cached)
    else Cache MISS
        CF->>S3: GET (with OAI)
        S3-->>CF: 200 OK
        CF-->>Browser: 200 OK + cache
    end
```

### REST API Request

```mermaid
sequenceDiagram
    participant Browser
    participant CF as CloudFront
    participant ALB
    participant EC2
    participant RDS

    Browser->>CF: POST /api/v1/sessions
    CF->>ALB: Forward (HTTP)
    ALB->>EC2: Forward (:8000)
    EC2->>RDS: INSERT session
    RDS-->>EC2: OK
    EC2-->>Browser: 201 Created
```

### WebSocket Streaming (RAG Chat)

```mermaid
sequenceDiagram
    participant Browser
    participant CF as CloudFront
    participant ALB
    participant EC2
    participant Bedrock

    Note over Browser,EC2: WebSocket Handshake
    Browser->>CF: GET /ws/chat<br/>Upgrade: websocket
    CF->>ALB: Forward (HTTP/1.1)
    ALB->>EC2: Forward (:8000)
    EC2-->>Browser: 101 Switching Protocols

    Note over Browser,EC2: WebSocket Stream
    Browser->>EC2: {"message": "Question?"}
    EC2->>Bedrock: Embed + Query

    loop Token Streaming
        Bedrock-->>EC2: {"token": "..."}
        EC2-->>Browser: {"token": "..."}
    end
```

---

## 📁 Project Structure

```
IAC/
├── __main__.py              # 🎯 Entry point: Orchestrates all components
├── Pulumi.yaml              # Base config
├── Pulumi.dev.yaml          # Dev environment overrides
├── Pulumi.prod.yaml         # Prod environment overrides
│
├── configs/
│   ├── constants.py         # CIDRs, ports, defaults
│   ├── base.py              # EnvironmentConfig dataclass
│   └── environment.py       # Config loader
│
├── utils/
│   ├── naming.py            # Resource naming conventions
│   └── tags.py              # AWS tagging factory
│
├── components/
│   ├── networking/
│   │   ├── vpc.py           # VPC, subnets, route tables
│   │   ├── security_groups.py # 5 security groups
│   │   └── vpc_endpoints.py # S3, SQS, Bedrock, Secrets endpoints
│   │
│   ├── security/
│   │   ├── iam_roles.py     # EC2, Lambda execution roles
│   │   └── secrets_manager.py # API keys, DB credentials
│   │
│   ├── storage/
│   │   ├── s3_buckets.py    # Documents, Vectors, Frontend
│   │   ├── rds_postgres.py  # PostgreSQL database
│   │   └── ecr_repository.py # Lambda container images
│   │
│   ├── messaging/
│   │   └── sqs_queues.py    # Doc processing queue + DLQ
│   │
│   ├── compute/
│   │   ├── alb.py           # Application Load Balancer
│   │   ├── ec2_backend.py   # FastAPI backend instance
│   │   └── lambda_processor.py # Document processor
│   │
│   └── edge/
│       ├── cloudfront.py    # CDN distribution
│       └── api_gateway.py   # HTTP API with VPC Link
│
└── diagrams/
    ├── NETWORKING_DEEP_DIVE.md      # 🎓 Protocol & troubleshooting guide
    └── IAC_COMPREHENSIVE_GUIDE.md   # Complete code walkthrough
```

---

## 🚀 Deployment

### Prerequisites

```powershell
# Install Pulumi
choco install pulumi

# Install AWS CLI
choco install awscli

# Configure AWS credentials
aws configure
```

### Deploy

```powershell
# Navigate to IAC directory
cd IAC

# Select environment
pulumi stack select dev

# Preview changes
pulumi preview

# Deploy
pulumi up

# View outputs
pulumi stack output
```

### Common Issues

| Issue                 | Cause                   | Solution                                   |
| --------------------- | ----------------------- | ------------------------------------------ |
| WebSocket 1006        | ALB timeout too short   | Set `idle_timeout=600`                     |
| 502 Bad Gateway       | EC2 unhealthy           | Check /api/v1/health endpoint              |
| Can't create ALB      | Subnet misconfiguration | Use public subnets for internet-facing ALB |
| No AWS service access | Missing VPC endpoints   | Create endpoints for S3, Bedrock, SQS      |

> 📖 **For detailed troubleshooting flowcharts, see [NETWORKING_DEEP_DIVE.md](diagrams/NETWORKING_DEEP_DIVE.md#common-deployment-issues--troubleshooting)**

---

## 🔧 Key Configuration Values

### Networking

| Setting        | Value         | File                 |
| -------------- | ------------- | -------------------- |
| VPC CIDR       | 10.0.0.0/16   | configs/constants.py |
| Public Subnet  | 10.0.0.0/24   | configs/constants.py |
| Private Subnet | 10.0.1.0/24   | configs/constants.py |
| Lambda Subnet  | 10.0.2.0/24   | configs/constants.py |
| Data Subnets   | 10.0.3-4.0/24 | configs/constants.py |

### Timeouts

| Setting               | Value | Purpose                  |
| --------------------- | ----- | ------------------------ |
| ALB Idle Timeout      | 600s  | WebSocket keep-alive     |
| Target Deregistration | 300s  | Graceful shutdown        |
| Health Check Interval | 30s   | Target health monitoring |

### Protocols

| Path                 | Protocol         | Encryption        |
| -------------------- | ---------------- | ----------------- |
| Browser → CloudFront | HTTPS (TLS 1.2+) | ✅                |
| CloudFront → ALB     | HTTP/1.1         | ❌ (AWS backbone) |
| ALB → EC2            | HTTP             | ❌ (VPC internal) |
| EC2 → RDS            | PostgreSQL       | ❌ (VPC internal) |

---

## 📚 Learn More

- **[NETWORKING_DEEP_DIVE.md](diagrams/NETWORKING_DEEP_DIVE.md)** - Protocol flows, security zones, troubleshooting
- **[IAC_COMPREHENSIVE_GUIDE.md](diagrams/IAC_COMPREHENSIVE_GUIDE.md)** - Complete code walkthrough with patterns

---

_Infrastructure as Code for Student Helper RAG Application_
_Built with Pulumi + Python + AWS_
