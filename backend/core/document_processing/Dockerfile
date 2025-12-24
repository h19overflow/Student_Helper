#
# AWS Lambda Docker image for document processing.
#
# Uses AWS Lambda Python 3.11 base image with:
# - Core dependencies (Pydantic, LangChain)
# - PDF parsing (pypdf via langchain-community)
# - AWS SDK (boto3, langchain-aws for S3 Vectors)
# - Database (SQLAlchemy + asyncpg for RDS)
# - Embeddings (langchain-google-genai)
#
# Image size: ~1GB
#

FROM public.ecr.aws/lambda/python:3.11

# Set Lambda task root
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy requirements first (layer caching optimization)
COPY backend/core/document_processing/requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt

# Upgrade pip and install Python dependencies
# Pre-install numpy with prebuilt wheels to avoid source compilation
RUN pip install --upgrade pip && \
    pip install --no-cache-dir "numpy>=1.26.0,<2.0.0" && \
    pip install --no-cache-dir -r requirements.txt

# Copy document_processing module (self-contained)
COPY backend/core/document_processing/ ${LAMBDA_TASK_ROOT}/backend/core/document_processing/
COPY backend/__init__.py ${LAMBDA_TASK_ROOT}/backend/
COPY backend/core/exceptions.py ${LAMBDA_TASK_ROOT}/backend/core/

# Create minimal backend/core/__init__.py for Lambda (excludes session module)
RUN echo '"""Core module for Lambda."""' > ${LAMBDA_TASK_ROOT}/backend/core/__init__.py

# Set environment variables for Lambda
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="${LAMBDA_TASK_ROOT}:${PATH}"

# Set the Lambda handler
# Format: module.submodule.handler_function
CMD ["backend.core.document_processing.lambda_handler.handler"]
