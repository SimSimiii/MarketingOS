"""AI provider abstraction. Business/agent code depends only on `AIProvider`,
never on a specific vendor SDK. Use `get_ai_provider()` to obtain an instance."""

from app.ai.base import AIMessage, AIProvider, AIRequest, AIResponse
from app.ai.factory import get_ai_provider

__all__ = ["AIMessage", "AIProvider", "AIRequest", "AIResponse", "get_ai_provider"]
