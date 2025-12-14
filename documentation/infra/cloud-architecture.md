# Cloud Architecture

AWS infrastructure for the Legal Search RAG application.

## Overview

Three-tier architecture with edge services, compute layer, and managed data stores.

## Architecture Diagram

```mermaid
flowchart TB
    subgraph Internet
        User[👤 User]
    end

    subgraph AWS[AWS Cloud]

        subgraph Edge[Public - Edge Layer]
            CF[CloudFront]
            S3_FE[S3 Bucket<br/>Frontend Static]
            APIGW[API Gateway]
        end

        subgraph VPC[VPC 10.0.0.0/16]

            subgraph PrivateSubnet[Private Subnet 10.0.1.0/24]
                EC2[EC2 t3.small<br/>FastAPI Backend]
            end

            subgraph LambdaSubnet[Lambda Subnet 10.0.2.0/24]
                Lambda[Lambda<br/>Doc Processor]
            end

            subgraph DataSubnet[Data Subnet 10.0.3.0/24]
                RDS[(RDS PostgreSQL)]
            end

            subgraph Endpoints[VPC Endpoints]
                S3_EP[S3 Gateway Endpoint]
                SQS_EP[SQS Interface Endpoint]
                Secrets_EP[Secrets Manager Endpoint]
                Bedrock_EP[Bedrock Runtime Endpoint]
            end

        end

        subgraph PrivateAWS[Private AWS Services]
            S3_Docs[S3 Bucket<br/>Documents]
            S3_Vec[S3 Vectors<br/>Embeddings]
            SQS[SQS Queue]
            DLQ[SQS DLQ]
            Secrets[Secrets Manager]
            ECR[ECR Repository<br/>Lambda Images]
        end

    end

    %% User flows
    User -->|HTTPS| CF
    CF -->|serves static| S3_FE
    S3_FE -.->|fetch /api calls| APIGW

    %% API Gateway to backend
    APIGW -->|VPC Link| EC2

    %% EC2 connections
    EC2 --> S3_EP
    EC2 --> SQS_EP
    EC2 --> Secrets_EP
    EC2 --> Bedrock_EP
    EC2 --> RDS

    %% Lambda connections
    Lambda --> S3_EP
    Lambda --> Secrets_EP
    Lambda --> Bedrock_EP
    Lambda --> RDS
    Lambda -.->|pulls image| ECR

    %% VPC Endpoints to services
    S3_EP --> S3_Docs
    S3_EP --> S3_Vec
    SQS_EP --> SQS
    SQS --> DLQ
    Secrets_EP --> Secrets
    Bedrock_EP -.->|AWS Bedrock| AWS[AWS Bedrock Service]

    %% SQS triggers Lambda
    SQS -->|trigger| Lambda
```

## Component Summary

| Layer | Subnet | Service | Purpose |
|-------|--------|---------|---------|
| Public | - | CloudFront | CDN for frontend |
| Public | - | S3 (Frontend) | Static assets |
| Public | - | API Gateway | API routing via VPC Link |
| VPC | Private | EC2 | FastAPI backend |
| VPC | Lambda | Lambda | Document processing |
| VPC | Data | RDS PostgreSQL | Sessions, jobs, metadata |
| VPC | Endpoints | S3 Gateway | Private S3 access |
| VPC | Endpoints | SQS Interface | Private SQS access |
| VPC | Endpoints | Secrets Manager | Private secrets access |
| VPC | Endpoints | Bedrock Runtime | Private Bedrock access |
| Private AWS | - | S3 (Documents) | Uploaded PDFs |
| Private AWS | - | S3 Vectors | Vector embeddings |
| Private AWS | - | SQS + DLQ | Job queue |
| Private AWS | - | Secrets Manager | API keys |
| Private AWS | - | ECR Repository | Lambda container images (up to 10GB) |

## Security Groups

| Security Group | Inbound | Outbound |
|----------------|---------|----------|
| sg-backend | 8000 from API Gateway VPC Link | RDS, Endpoints, Bedrock API |
| sg-lambda | SQS trigger (AWS managed) | RDS, Endpoints, Bedrock API |
| sg-database | 5432 from sg-backend, sg-lambda | None |
| sg-endpoints | 443 from sg-backend, sg-lambda | AWS Services |
