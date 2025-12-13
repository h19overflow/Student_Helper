"""
Pulumi infrastructure-as-code for Student Helper RAG application.

This package defines AWS infrastructure including:
- VPC with private subnets for compute and data layers
- EC2 for FastAPI backend
- Lambda for document processing
- RDS PostgreSQL for persistence
- S3 buckets for documents, vectors, and frontend
- SQS for async job processing
- CloudFront CDN and API Gateway for edge layer
"""
