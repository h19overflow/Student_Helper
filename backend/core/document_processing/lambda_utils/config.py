"""
Configuration and secrets management utilities for Lambda.
"""

import json
import logging
import os
import boto3
from typing import Dict
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


def validate_environment() -> Dict[str, str]:
    """
    Validate required environment variables.
    """
    required_vars = [
        "DOCUMENTS_BUCKET",
        "VECTORS_BUCKET",
        "DATABASE_URL",
        "AWS_REGION",
    ]

    env_config = {}
    missing = []

    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
        else:
            env_config[var] = value

    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    logger.info("validate_environment - Environment validated")
    return env_config


def configure_secrets() -> None:
    """
    Fetch access secrets from Secrets Manager and update environment.
    """
    session = boto3.session.Session()
    client = session.client("secretsmanager")
    
    # 1. Configure Database Password
    db_url = os.getenv("DATABASE_URL", "")
    db_secret_arn = os.getenv("DB_SECRET_ARN")
    
    if "placeholder" in db_url and db_secret_arn:
        try:
            response = client.get_secret_value(SecretId=db_secret_arn)
            if "SecretString" in response:
                secret = json.loads(response["SecretString"])
                password = secret.get("password")
                
                if password:
                    safe_password = quote_plus(password)
                    new_url = db_url.replace("placeholder", safe_password)
                    os.environ["DATABASE_URL"] = new_url
                    logger.info("configure_secrets - Updated DATABASE_URL with secret")
        except Exception as e: # pylint: disable=broad-except
            logger.error("configure_secrets - Failed to fetch DB secret: %s", e)

    # 2. Configure Google API Key
    google_secret_arn = os.getenv("SECRETS_ARN")
    if google_secret_arn:
        try:
            response = client.get_secret_value(SecretId=google_secret_arn)
            if "SecretString" in response:
                secret = json.loads(response["SecretString"])
                api_key = secret.get("api_key")
                
                if api_key and api_key != "PLACEHOLDER_SET_VIA_CLI":
                    os.environ["GOOGLE_API_KEY"] = api_key
                    os.environ["GEMINI_API_KEY"] = api_key
                    logger.info("configure_secrets - Set GOOGLE_API_KEY from secret")
                else:
                    logger.warning("configure_secrets - Google API Key is missing or placeholder")
        except Exception as e: # pylint: disable=broad-except
            logger.error("configure_secrets - Failed to fetch Google API Key: %s", e)
