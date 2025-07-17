"""LLM integration module for memory management."""

from .client import LLMClient
from .prompts import PromptTemplates

__all__ = ['LLMClient', 'PromptTemplates']