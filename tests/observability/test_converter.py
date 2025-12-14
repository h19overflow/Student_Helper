"""Tests for LangChain to Langfuse converter."""

import pytest
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

from backend.observability.prompt_registry.converter import (
    _convert_variables,
    convert_chat_template,
    convert_text_template,
)


class TestVariableConversion:
    """Tests for variable syntax conversion."""

    def test_single_variable(self) -> None:
        """Convert single variable from {var} to {{var}}."""
        result = _convert_variables("Hello {name}!")
        assert result == "Hello {{name}}!"

    def test_multiple_variables(self) -> None:
        """Convert multiple variables."""
        result = _convert_variables("Hello {first} {last}!")
        assert result == "Hello {{first}} {{last}}!"

    def test_no_variables(self) -> None:
        """Text without variables unchanged."""
        result = _convert_variables("Hello world!")
        assert result == "Hello world!"

    def test_already_doubled(self) -> None:
        """Already doubled braces unchanged."""
        result = _convert_variables("Hello {{name}}!")
        assert result == "Hello {{name}}!"

    def test_empty_braces(self) -> None:
        """Empty braces handled."""
        result = _convert_variables("Hello {}!")
        # Empty braces should not match the pattern
        assert result == "Hello {}!"

    def test_mixed_content(self) -> None:
        """Mix of text and variables."""
        result = _convert_variables("User {user} asked: {question}")
        assert result == "User {{user}} asked: {{question}}"


class TestChatTemplateConversion:
    """Tests for ChatPromptTemplate conversion."""

    def test_simple_chat_template(self) -> None:
        """Convert simple chat template."""
        template = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant."),
            ("human", "Hello!"),
        ])
        result = convert_chat_template(template)

        assert len(result) == 2
        assert result[0] == {"role": "system", "content": "You are a helpful assistant."}
        assert result[1] == {"role": "user", "content": "Hello!"}

    def test_chat_template_with_variables(self) -> None:
        """Convert chat template with variables."""
        template = ChatPromptTemplate.from_messages([
            ("system", "You are a {role} assistant."),
            ("human", "{question}"),
        ])
        result = convert_chat_template(template)

        assert result[0] == {"role": "system", "content": "You are a {{role}} assistant."}
        assert result[1] == {"role": "user", "content": "{{question}}"}

    def test_chat_template_all_roles(self) -> None:
        """Convert template with all role types."""
        template = ChatPromptTemplate.from_messages([
            ("system", "System message"),
            ("human", "User message"),
            ("ai", "Assistant message"),
        ])
        result = convert_chat_template(template)

        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
        assert result[2]["role"] == "assistant"

    def test_empty_template(self) -> None:
        """Convert empty template."""
        template = ChatPromptTemplate.from_messages([])
        result = convert_chat_template(template)

        assert result == []


class TestTextTemplateConversion:
    """Tests for PromptTemplate conversion."""

    def test_simple_text_template(self) -> None:
        """Convert simple text template."""
        template = PromptTemplate.from_template("Hello world!")
        result = convert_text_template(template)

        assert result == "Hello world!"

    def test_text_template_with_variables(self) -> None:
        """Convert text template with variables."""
        template = PromptTemplate.from_template("Hello {name}, how is {topic}?")
        result = convert_text_template(template)

        assert result == "Hello {{name}}, how is {{topic}}?"

    def test_multiline_text_template(self) -> None:
        """Convert multiline text template."""
        template = PromptTemplate.from_template(
            "Line 1: {first}\nLine 2: {second}"
        )
        result = convert_text_template(template)

        assert result == "Line 1: {{first}}\nLine 2: {{second}}"
