"""
Tag factory for AWS resources.

Provides consistent tagging for cost allocation and resource management.
"""

from IAC.configs.constants import DEFAULT_TAGS


def create_tags(
    environment: str,
    resource_name: str,
    **extra_tags: str,
) -> dict[str, str]:
    """
    Create a standard tag set for an AWS resource.

    Args:
        environment: Deployment environment
        resource_name: Name of the resource
        **extra_tags: Additional tags to include

    Returns:
        Dictionary of tags
    """
    tags = {
        **DEFAULT_TAGS,
        "Environment": environment,
        "Name": resource_name,
    }
    tags.update(extra_tags)
    return tags


def merge_tags(
    base_tags: dict[str, str],
    *additional_tags: dict[str, str],
) -> dict[str, str]:
    """
    Merge multiple tag dictionaries.

    Args:
        base_tags: Base tag dictionary
        *additional_tags: Additional tag dictionaries to merge

    Returns:
        Merged tag dictionary
    """
    result = base_tags.copy()
    for tags in additional_tags:
        result.update(tags)
    return result
