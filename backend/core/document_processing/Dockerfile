#
# Uses AWS Lambda Python 3.11 base image with:
# - Core dependencies (Pydantic, LangChain)
# - Document processing (Docling)
# - AWS SDK (boto3, asyncpg for async RDS)
# - Structured logging (structlog)
#
# Builds ~2.5GB image with all dependencies included.

FROM public.ecr.aws/lambda/python:3.11

# Set Lambda task root
WORKDIR ${LAMBDA_TASK_ROOT}

# Install system dependencies for PDF processing and database drivers
RUN yum update -y && \
    yum install -y \
        libpq-devel \
        postgresql15-devel \
        && \
    yum clean all

# Copy requirements first (layer caching optimization)
COPY backend/core/document_processing/requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt asyncpg==0.29.0

# Copy only document_processing module (self-contained, no external dependencies)
COPY backend/core/document_processing/ ${LAMBDA_TASK_ROOT}/backend/core/document_processing/
COPY backend/__init__.py ${LAMBDA_TASK_ROOT}/backend/
COPY backend/core/__init__.py ${LAMBDA_TASK_ROOT}/backend/core/

# Create non-root user for security (Lambda runs as root by default, but best practice)
# Note: AWS Lambda requires specific permissions, so we keep root for now

# Set environment variables for Lambda
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="${LAMBDA_TASK_ROOT}:${PATH}"

# Health check (optional - verifies image)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "from backend.core.document_processing import lambda_handler; print('OK')" || exit 1

# Set the Lambda handler
# Format: module.submodule.handler_function
CMD ["backend.core.document_processing.lambda_handler.handler"]
