# 📚 Documentation Index

## Student Helper Project Documentation

**Last Updated:** 2025-12-18

---

## 📖 How to Use This Documentation

This documentation is organized into **4 main categories** by functionality:

1.  **Architecture** - High-level system design and protocol analysis
2.  **Networking** - VPC, Security Groups, and connectivity details
3.  **Troubleshooting** - Post-mortems of major issues and fixes
4.  **Implementation Guides** - Step-by-step guides for specific features

---

## 🏗️ 01. Architecture

**Purpose:** Understand the overall system design, protocol transitions, and component interactions.

| Document                                                                         | Description                                                                                                                                                               |
| -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **[COMPONENT_ANALYSIS_REPORT.md](01_architecture/COMPONENT_ANALYSIS_REPORT.md)** | 📘 **START HERE** - Comprehensive breakdown of every AWS component (CloudFront, API Gateway, VPC Links, Load Balancers, IAM) with technical specs, rules, and challenges. |
| **[PROTOCOL_DEEP_DIVE.md](01_architecture/PROTOCOL_DEEP_DIVE.md)**               | Deep technical analysis of protocol transitions from Core (EC2) to Cloud (CloudFront), including the 3 major setbacks we solved.                                          |
| **[PROTOCOL_MASTER_REPORT.md](01_architecture/PROTOCOL_MASTER_REPORT.md)**       | High-level overview of the dual-path routing strategy (REST vs WebSocket).                                                                                                |
| **[infra/cloud-architecture.md](01_architecture/infra/cloud-architecture.md)**   | Mermaid diagrams showing the complete infrastructure layout.                                                                                                              |

**Key Topics:**

- Layer-by-layer architecture (Core → Cloud)
- ALB vs NLB differences
- VPC Link v1 vs v2 compatibility
- Security Group matrix

---

## 🌐 02. Networking

**Purpose:** Understand VPC configuration, security groups, and network-level troubleshooting.

| Document                                                                         | Description                                                                                                       |
| -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **[AWS_NETWORKING_VS_IAM.md](02_networking/AWS_NETWORKING_VS_IAM.md)**           | Explains the difference between networking (Security Groups) and permissions (IAM), plus the VPC Link egress fix. |
| **[VPC_LINK_EGRESS_FIX.md](02_networking/VPC_LINK_EGRESS_FIX.md)**               | How we fixed the "self-reference" security group issue for VPC Link → ALB communication.                          |
| **[EC2_PRIVATE_SUBNET_LESSONS.md](02_networking/EC2_PRIVATE_SUBNET_LESSONS.md)** | Lessons learned from deploying EC2 in a private subnet with no internet access.                                   |

**Key Topics:**

- Security Group rules (ingress/egress)
- VPC Link ENI behavior
- Private subnet isolation

---

## 🔧 03. Troubleshooting

**Purpose:** Post-mortems of major issues, root cause analysis, and solutions.

### Major Setbacks (Critical Issues)

| Document                                                                                                                              | Description                                                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| **[MAJOR_SETBACK/README.md](03_troubleshooting/MAJOR_SETBACK/README.md)**                                                             | 📕 **Overview of all 3 major setbacks** (12 hours total debugging time).                      |
| **[MAJOR_SETBACK/INFERENCE_PROFILE_DISCOVERY.md](03_troubleshooting/MAJOR_SETBACK/INFERENCE_PROFILE_DISCOVERY.md)**                   | The IAM "Identity Crisis" - Why cross-region Bedrock models require `inference-profile` ARNs. |
| **[MAJOR_SETBACK/VPC_LINK_AND_LOAD_BALANCER_DEEP_DIVE.md](03_troubleshooting/MAJOR_SETBACK/VPC_LINK_AND_LOAD_BALANCER_DEEP_DIVE.md)** | The VPC Link v2 incompatibility - Why we needed NLB + VPC Link v1 for WebSockets.             |
| **[MAJOR_SETBACK/NLB_SECURITY_GROUP_BLOCKING.md](03_troubleshooting/MAJOR_SETBACK/NLB_SECURITY_GROUP_BLOCKING.md)**                   | The "Invisible Firewall" - Why NLB traffic requires CIDR-based security rules.                |
| **[MAJOR_SETBACK/HTTP_API_NO_WEBSOCKET.md](03_troubleshooting/MAJOR_SETBACK/HTTP_API_NO_WEBSOCKET.md)**                               | Why HTTP API cannot handle WebSocket connections.                                             |

### WebSocket Issues

| Document                                                                                    | Description                                                |
| ------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| **[WEBSOCKET_CONNECTION_PROBLEM.md](03_troubleshooting/WEBSOCKET_CONNECTION_PROBLEM.md)**   | Initial WebSocket connection failures and debugging steps. |
| **[WEBSOCKET_FIX_SUMMARY.md](03_troubleshooting/WEBSOCKET_FIX_SUMMARY.md)**                 | Summary of all WebSocket fixes applied.                    |
| **[WEBSOCKET_BLOCKING_ANALYSIS.md](03_troubleshooting/WEBSOCKET_BLOCKING_ANALYSIS.md)**     | Event loop blocking issues in FastAPI WebSocket handlers.  |
| **[WEBSOCKET_IMPLEMENTATION.md](03_troubleshooting/WEBSOCKET_IMPLEMENTATION.md)**           | Original WebSocket implementation notes.                   |
| **[WEBSOCKET_VPC_LINK_LIMITATION.md](03_troubleshooting/WEBSOCKET_VPC_LINK_LIMITATION.md)** | VPC Link v2 limitations for WebSocket APIs.                |

### General Troubleshooting

| Document                                                                          | Description                                                 |
| --------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| **[TROUBLESHOOTING_503.md](03_troubleshooting/TROUBLESHOOTING_503.md)**           | Complete guide to debugging 503 Service Unavailable errors. |
| **[DEBUGGING_SESSION_ISSUES.md](03_troubleshooting/DEBUGGING_SESSION_ISSUES.md)** | Session management and state issues.                        |
| **[RDS_CONNECTION_ISSUES.md](03_troubleshooting/RDS_CONNECTION_ISSUES.md)**       | Database connectivity problems and solutions.               |
| **[IAM_BEDROCK_FIX.md](03_troubleshooting/IAM_BEDROCK_FIX.md)**                   | IAM permission fixes for Bedrock access.                    |

### Alternative Approaches

| Document                                                          | Description                                                   |
| ----------------------------------------------------------------- | ------------------------------------------------------------- |
| **[api_gw_bypass_plan/](03_troubleshooting/api_gw_bypass_plan/)** | Research on bypassing API Gateway entirely (not implemented). |

---

## 📝 04. Implementation Guides

**Purpose:** Step-by-step guides for implementing specific features.

| Document                                                                                          | Description                                                         |
| ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| **[PRESIGNED_URL_S3_UPLOAD_GUIDE.md](04_implementation_guides/PRESIGNED_URL_S3_UPLOAD_GUIDE.md)** | Complete guide to implementing presigned URL uploads for documents. |
| **[MULTIPART_UPLOAD_PATTERN.md](04_implementation_guides/MULTIPART_UPLOAD_PATTERN.md)**           | Pattern for handling large file uploads with multipart.             |
| **[S3BucketCorsChange.md](04_implementation_guides/S3BucketCorsChange.md)**                       | How to configure CORS for S3 buckets.                               |
| **[FORMALIZING_GUIDE.md](04_implementation_guides/FORMALIZING_GUIDE.md)**                         | Guide to formalizing the codebase structure.                        |
| **[project_plan/](04_implementation_guides/project_plan/)**                                       | Original project planning documents.                                |
| **[service_level/](04_implementation_guides/service_level/)**                                     | Service-level documentation.                                        |

---

## 🎯 Quick Reference

### For New Team Members

1.  Start with **[COMPONENT_ANALYSIS_REPORT.md](01_architecture/COMPONENT_ANALYSIS_REPORT.md)** to understand the architecture
2.  Read **[MAJOR_SETBACK/README.md](03_troubleshooting/MAJOR_SETBACK/README.md)** to learn what NOT to do
3.  Reference **[TROUBLESHOOTING_503.md](03_troubleshooting/TROUBLESHOOTING_503.md)** when things break

### For Debugging

1.  **503 Errors** → [TROUBLESHOOTING_503.md](03_troubleshooting/TROUBLESHOOTING_503.md)
2.  **WebSocket Issues** → [WEBSOCKET_FIX_SUMMARY.md](03_troubleshooting/WEBSOCKET_FIX_SUMMARY.md)
3.  **IAM/Bedrock Errors** → [IAM_BEDROCK_FIX.md](03_troubleshooting/IAM_BEDROCK_FIX.md)
4.  **Security Group Issues** → [NLB_SECURITY_GROUP_BLOCKING.md](03_troubleshooting/MAJOR_SETBACK/NLB_SECURITY_GROUP_BLOCKING.md)

### For Architecture Decisions

1.  **Why dual load balancers?** → [VPC_LINK_AND_LOAD_BALANCER_DEEP_DIVE.md](03_troubleshooting/MAJOR_SETBACK/VPC_LINK_AND_LOAD_BALANCER_DEEP_DIVE.md)
2.  **Why separate API Gateways?** → [HTTP_API_NO_WEBSOCKET.md](03_troubleshooting/MAJOR_SETBACK/HTTP_API_NO_WEBSOCKET.md)
3.  **Protocol transitions?** → [PROTOCOL_DEEP_DIVE.md](01_architecture/PROTOCOL_DEEP_DIVE.md)

---

## 📊 Documentation Statistics

- **Total Documents:** 30+
- **Total Debugging Time Documented:** ~12 hours
- **Major Issues Resolved:** 3
- **Architecture Layers Documented:** 6

---

_Documentation maintained by the Student Helper development team_
