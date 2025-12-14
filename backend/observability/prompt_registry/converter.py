"""
LangChain to Langfuse prompt converter.

Handles conversion between LangChain ChatPromptTemplate format and Langfuse
chat message format with variable syntax transformation.

Dependencies: langchain_core.prompts
System role: Template format conversion for prompt registry
"""

import re
from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.prompts.chat import (
    AIMessagePromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)


class LangfuseMessage(TypedDict):
    """Langfuse chat message format."""

    role: str
    content: str


def _convert_variables(content: str) -> str:
    """
    Convert LangChain variable syntax to Langfuse format.

    LangChain uses {variable} while Langfuse uses {{variable}}.

    Args:
        content: Template string with LangChain variables

    Returns:
        str: Template string with Langfuse variables
    """
    # Match single braces not already doubled
    # Negative lookbehind/ahead to avoid already-doubled braces
    pattern = r"(?<!\{)\{([^{}]+)\}(?!\})"
    return re.sub(pattern, r"{{\1}}", content)


def _get_role_from_message(message: object) -> str:
    """
    Extract role from LangChain message template.

    Args:
        message: LangChain message prompt template

    Returns:
        str: Role name (system, user, assistant)

    Raises:
        ValueError: If message type is unsupported
    """
    if isinstance(message, SystemMessagePromptTemplate):
        return "system"
    if isinstance(message, HumanMessagePromptTemplate):
        return "user"
    if isinstance(message, AIMessagePromptTemplate):
        return "assistant"

    # Handle tuple format (role, content)
    if isinstance(message, tuple) and len(message) == 2:
        role_map = {"system": "system", "human": "user", "ai": "assistant"}
        role = str(message[0]).lower()
        return role_map.get(role, role)

    raise ValueError(f"Unsupported message type: {type(message)}")


def _get_content_from_message(message: object) -> str:
    """
    Extract content template from LangChain message.

    Args:
        message: LangChain message prompt template

    Returns:
        str: Content template string
    """
    # Handle MessagePromptTemplate subclasses
    if hasattr(message, "prompt") and hasattr(message.prompt, "template"):
        return str(message.prompt.template)

    # Handle tuple format (role, content)
    if isinstance(message, tuple) and len(message) == 2:
        return str(message[1])

    raise ValueError(f"Cannot extract content from: {type(message)}")


def convert_chat_template(template: ChatPromptTemplate) -> list[LangfuseMessage]:
    """
    Convert LangChain ChatPromptTemplate to Langfuse message format.

    Transforms message list and converts variable syntax from {var} to {{var}}.

    Args:
        template: LangChain ChatPromptTemplate instance

    Returns:
        list[LangfuseMessage]: List of Langfuse-formatted messages

    Raises:
        ValueError: If template contains unsupported message types

    Example:
        >>> template = ChatPromptTemplate.from_messages([
        ...     ("system", "You are a {role}"),
        ...     ("human", "{question}")
        ... ])
        >>> messages = convert_chat_template(template)
        >>> messages[0]
        {'role': 'system', 'content': 'You are a {{role}}'}
    """
    messages: list[LangfuseMessage] = []

    for msg in template.messages:
        role = _get_role_from_message(msg)
        content = _get_content_from_message(msg)
        langfuse_content = _convert_variables(content)

        messages.append(LangfuseMessage(role=role, content=langfuse_content))

    return messages


def convert_text_template(template: PromptTemplate) -> str:
    """
    Convert LangChain PromptTemplate to Langfuse text format.

    Converts variable syntax from {var} to {{var}}.

    Args:
        template: LangChain PromptTemplate instance

    Returns:
        str: Langfuse-formatted template string

    Example:
        >>> template = PromptTemplate.from_template("Hello {name}!")
        >>> text = convert_text_template(template)
        >>> text
        'Hello {{name}}!'
    """
    return _convert_variables(template.template)
