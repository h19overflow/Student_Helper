"""
AWS Student Helper RAG Application Architecture Diagram.

Generates detailed infrastructure diagram with VPC endpoints, VPC Links, and subnets.

Dependencies:
    pip install diagrams

Usage:
    python architecture_diagram.py
    # Outputs: student_helper_architecture.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2, Lambda, ECR
from diagrams.aws.database import RDS
from diagrams.aws.network import (
    VPC,
    PrivateSubnet,
    APIGateway,
    CloudFront,
    Endpoint,
    VPCElasticNetworkInterface,
)
from diagrams.aws.storage import S3
from diagrams.aws.integration import SQS
from diagrams.aws.security import SecretsManager, IAMRole
from diagrams.aws.ml import Bedrock
from diagrams.aws.general import Users, GenericDatabase

# Custom styling for detailed diagram
graph_attr = {
    "fontsize": "14",
    "bgcolor": "white",
    "pad": "0.5",
    "splines": "ortho",
    "nodesep": "0.8",
    "ranksep": "1.2",
    "dpi": "300",
}

node_attr = {
    "fontsize": "11",
    "height": "1.2",
    "width": "1.5",
}

edge_attr = {
    "fontsize": "9",
}


with Diagram(
    "Student Helper RAG Architecture\n(VPC Endpoints, VPC Links, and Private Subnets)",
    filename="student_helper_architecture",
    show=False,
    direction="TB",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr,
):
    # External users
    users = Users("Users\n(Internet)")

    # Edge Layer (Public, outside VPC)
    with Cluster("Edge Layer (Public - Outside VPC)"):
        cloudfront = CloudFront("CloudFront CDN\nGlobal Edge Locations\nHTTPS/TLS")
        api_gateway = APIGateway(
            "API Gateway HTTP API\nabc123.execute-api\nPublic Endpoint\nCORS Enabled"
        )

    # S3 Buckets (outside VPC, accessed via endpoints)
    with Cluster("Storage Layer (Outside VPC - Accessed Privately)"):
        s3_frontend = S3("Frontend Bucket\nstudent-helper-dev-frontend\nReact SPA Assets")
        s3_docs = S3(
            "Documents Bucket\nstudent-helper-dev-documents\nPDF Files\nVersioning + AES-256"
        )
        s3_vectors = S3(
            "Vectors Bucket\nS3 Vectors Index\n1536-dim (Titan v2)\nCosine Similarity"
        )
        ecr = ECR(
            "ECR Repository\nLambda Docker Images\nUp to 10GB\nVuln Scanning"
        )

    # AWS Managed Services (outside VPC)
    with Cluster("Security & ML Services (AWS Managed)"):
        secrets = SecretsManager(
            "Secrets Manager\nRDS Password\nAPI Keys\nAES-256 Encrypted"
        )
        bedrock = Bedrock(
            "AWS Bedrock\nClaude 3 Sonnet (Chat)\nTitan Embeddings v2\nServerless"
        )

    # Messaging (outside VPC)
    with Cluster("Messaging Layer (Outside VPC)"):
        sqs_queue = SQS(
            "SQS Queue\nstudent-helper-dev-doc-queue\n360s Visibility\n14d Retention"
        )
        dlq = SQS("Dead Letter Queue\n3 Max Retries\nOps Debugging")

    # IAM Roles
    with Cluster("IAM Security"):
        ec2_role = IAMRole(
            "EC2 Instance Role\nS3, SQS, Secrets\nRDS Connect"
        )
        lambda_role = IAMRole(
            "Lambda Execution Role\nS3, SQS, RDS\nECR Pull, Bedrock"
        )

    # Main VPC
    with Cluster("VPC: 10.0.0.0/16 (65,536 IPs)\nNO Internet Gateway | NO NAT Gateway"):
        vpc_resource = VPC("VPC\n10.0.0.0/16\nFully Private")

        # Compute Subnet
        with Cluster("Compute Subnet: 10.0.1.0/24 (256 IPs)\nAvailability Zone: us-east-1a"):
            compute_subnet = PrivateSubnet("Private Subnet\n10.0.1.0/24")

            ec2 = EC2(
                "EC2 t3.small\nFastAPI Backend\nPrivate IP: 10.0.1.50\nPort: 8000\nNO Public IP"
            )

            # VPC Link ENI (in same subnet as EC2)
            vpc_link_eni = VPCElasticNetworkInterface(
                "VPC Link ENI\n10.0.1.100\nBridge: API GW → EC2\nSecurity Group: backend-sg"
            )

        # Lambda Subnet
        with Cluster("Lambda Subnet: 10.0.2.0/24 (256 IPs)\nAvailability Zone: us-east-1b"):
            lambda_subnet = PrivateSubnet("Private Subnet\n10.0.2.0/24")

            lambda_fn = Lambda(
                "Lambda Processor\nPython 3.11\nPrivate IP: 10.0.2.15\n512MB-1GB Memory\nDocument Processing"
            )

            # VPC Endpoint ENIs (Interface endpoints in Lambda subnet)
            with Cluster("VPC Endpoints (PrivateLink ENIs)"):
                sqs_endpoint = VPCElasticNetworkInterface(
                    "SQS Endpoint ENI\n10.0.2.45\nPort 443\nprivate_dns: true\nsqs.amazonaws.com"
                )

                secrets_endpoint = VPCElasticNetworkInterface(
                    "Secrets Endpoint ENI\n10.0.2.46\nPort 443\nprivate_dns: true\nsecretsmgr.*.com"
                )

                bedrock_endpoint = VPCElasticNetworkInterface(
                    "Bedrock Endpoint ENI\n10.0.2.47\nPort 443\nprivate_dns: true\nbedrock-runtime.*.com"
                )

            # S3 Gateway Endpoint (route table, not ENI)
            s3_gateway_endpoint = Endpoint(
                "S3 Gateway Endpoint\nRoute Table Entry\npl-63a5400a\nFREE (No ENI)"
            )

        # Data Subnet
        with Cluster("Data Subnet: 10.0.3.0/24 (256 IPs)\nAvailability Zone: us-east-1a"):
            data_subnet = PrivateSubnet("Private Subnet\n10.0.3.0/24")

            rds_primary = RDS(
                "RDS PostgreSQL 16\nPrimary Instance\nPrivate IP: 10.0.3.20\nPort: 5432\nt3.small"
            )

            rds_standby = GenericDatabase(
                "RDS Standby Replica\nMulti-AZ\nAuto Failover\nus-east-1b"
            )

    # =============================================================================
    # USER FLOWS
    # =============================================================================

    # Flow 1: Frontend access
    users >> Edge(label="HTTPS", color="orange", style="bold") >> cloudfront
    cloudfront >> Edge(label="Origin Fetch\nStatic Assets", color="lightblue") >> s3_frontend

    # Flow 2: API calls
    users >> Edge(label="API Request\nGET /api/v1/sessions", color="orange", style="bold") >> api_gateway

    # VPC Link connection (API Gateway → EC2)
    api_gateway >> Edge(
        label="VPC Link\nHTTP_PROXY\nconnection_type: VPC_LINK",
        color="green",
        style="bold"
    ) >> vpc_link_eni

    vpc_link_eni >> Edge(
        label="Private Network\nhttp://10.0.1.50:8000/{proxy}",
        color="green",
        style="bold"
    ) >> ec2

    # Flow 3: EC2 → RDS
    ec2 >> Edge(
        label="SQL Queries\nPort 5432\npsycopg2",
        color="darkblue",
        style="dashed"
    ) >> rds_primary

    rds_primary >> Edge(
        label="Async Replication",
        color="gray",
        style="dotted"
    ) >> rds_standby

    # Flow 4: EC2 → S3 (via Gateway Endpoint)
    ec2 >> Edge(
        label="boto3.client('s3')\nVia Route Table",
        color="green",
        style="dashed"
    ) >> s3_gateway_endpoint

    s3_gateway_endpoint >> Edge(
        label="pl-63a5400a\nPrivate Access",
        color="green"
    ) >> s3_docs

    s3_gateway_endpoint >> Edge(
        label="Vector Operations",
        color="green"
    ) >> s3_vectors

    # Flow 5: EC2 → SQS (via VPC Endpoint with DNS hijacking)
    ec2 >> Edge(
        label="boto3.client('sqs')\nDNS: sqs.amazonaws.com",
        color="purple",
        style="dashed"
    ) >> sqs_endpoint

    sqs_endpoint >> Edge(
        label="PrivateLink\n10.0.2.45 → SQS",
        color="purple",
        style="bold"
    ) >> sqs_queue

    # Flow 6: EC2 → Secrets Manager (via VPC Endpoint)
    ec2 >> Edge(
        label="GetSecretValue\nRDS Password",
        color="gold",
        style="dashed"
    ) >> secrets_endpoint

    secrets_endpoint >> Edge(
        label="PrivateLink\n10.0.2.46 → Secrets",
        color="gold",
        style="bold"
    ) >> secrets

    # Flow 7: EC2 → Bedrock (via VPC Endpoint)
    ec2 >> Edge(
        label="Generate Embeddings\nClaude Chat",
        color="pink",
        style="dashed"
    ) >> bedrock_endpoint

    bedrock_endpoint >> Edge(
        label="PrivateLink\n10.0.2.47 → Bedrock",
        color="pink",
        style="bold"
    ) >> bedrock

    # Flow 8: SQS → Lambda trigger
    sqs_queue >> Edge(
        label="Event Trigger\nBatch Size: 1\nLong Polling",
        color="red",
        style="bold"
    ) >> lambda_fn

    sqs_queue >> Edge(
        label="Failed Messages\nAfter 3 Retries",
        color="red",
        style="dotted"
    ) >> dlq

    # Flow 9: Lambda → S3 (document processing)
    lambda_fn >> Edge(
        label="Fetch PDF\nParse with docling",
        color="green",
        style="dashed"
    ) >> s3_gateway_endpoint

    # Flow 10: Lambda → Bedrock (embeddings)
    lambda_fn >> Edge(
        label="Generate Embeddings\nTitan v2",
        color="pink",
        style="dashed"
    ) >> bedrock_endpoint

    # Flow 11: Lambda → RDS (job status)
    lambda_fn >> Edge(
        label="Update Job Status\njobs table",
        color="darkblue",
        style="dashed"
    ) >> rds_primary

    # Flow 12: Lambda → ECR (cold start)
    lambda_fn << Edge(
        label="Pull Image\nCold Start Only",
        color="lightblue",
        style="dotted"
    ) << ecr

    # Flow 13: IAM Role attachments
    ec2_role >> Edge(label="Attached To", color="gray", style="dotted") >> ec2
    lambda_role >> Edge(label="Attached To", color="gray", style="dotted") >> lambda_fn

print("✅ Diagram generated: student_helper_architecture.png")
print("\nKey features visualized:")
print("  - VPC Link ENI (10.0.1.100) bridging API Gateway → EC2")
print("  - VPC Endpoint ENIs (10.0.2.45-47) for SQS, Secrets, Bedrock")
print("  - S3 Gateway Endpoint (route table, not ENI)")
print("  - Private subnets with CIDR notation (10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24)")
print("  - All data flows with protocols and technical details")
print("\nNote: EC2 has NO public IP - fully private architecture!")
