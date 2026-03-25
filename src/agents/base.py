"""
BaseAgent — shared foundation for all agents in this project.

Supports both Anthropic (Claude) and OpenAI (GPT) out of the box.
Set provider="openai" to use GPT models instead of Claude.

Every agent:
  - Has a name, role description, model, and provider
  - Maintains a message history (for multi-turn)
  - Can call complete() for single-shot or chat() for stateful conversation
  - Can be reset between runs
"""

import logging
import os
from dataclasses import dataclass
from typing import Literal

log = logging.getLogger(__name__)

Provider = Literal["anthropic", "openai"]

AnthropicModel = Literal[
    "claude-haiku-4-5",
    "claude-sonnet-4-5",
    "claude-opus-4-5",
]
OpenAIModel = Literal[
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4-turbo",
]
Model = str  # accepts any string so users can pin exact versions

DEFAULT_MODEL: Model = "claude-haiku-4-5"
DEFAULT_PROVIDER: Provider = "anthropic"


@dataclass
class Message:
    role: Literal["user", "assistant"]
    content: str


class BaseAgent:
    """
    Thin wrapper around both Anthropic and OpenAI SDKs.
    Subclass this and override `system_prompt` to specialise behaviour.

    Args:
        model:      Model name. Anthropic default: claude-haiku-4-5
                    OpenAI default: gpt-4o-mini
        provider:   "anthropic" (default) or "openai"
        max_tokens: Maximum tokens in each response
    """

    name: str = "Agent"
    system_prompt: str = "You are a helpful AI assistant."

    def __init__(
        self,
        model: Model = DEFAULT_MODEL,
        provider: Provider = DEFAULT_PROVIDER,
        max_tokens: int = 1024,
    ):
        self.model = model
        self.provider = provider
        self.max_tokens = max_tokens
        self._history: list[Message] = []
        self._client = self._build_client()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(self, user_message: str) -> str:
        """Send a message and return the assistant reply (stateful — updates history)."""
        self._history.append(Message(role="user", content=user_message))
        reply = self._call_api(self._history)
        self._history.append(Message(role="assistant", content=reply))
        log.debug("[%s] → %s", self.name, reply[:120])
        return reply

    def complete(self, prompt: str) -> str:
        """Single-shot completion — does NOT update history."""
        return self._call_api([Message(role="user", content=prompt)])

    def reset(self) -> None:
        """Clear conversation history."""
        self._history = []

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_client(self):
        if self.provider == "anthropic":
            import anthropic

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise OSError("ANTHROPIC_API_KEY not set. Add it to your .env file.")
            return anthropic.Anthropic(api_key=api_key)
        elif self.provider == "openai":
            import openai

            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise OSError("OPENAI_API_KEY not set. Add it to your .env file.")
            return openai.OpenAI(api_key=api_key)
        else:
            raise ValueError(f"Unknown provider: {self.provider!r}. Use 'anthropic' or 'openai'.")

    def _call_api(self, messages: list[Message]) -> str:
        if self.provider == "anthropic":
            return self._call_anthropic(messages)
        else:
            return self._call_openai(messages)

    def _call_anthropic(self, messages: list[Message]) -> str:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=[{"role": m.role, "content": m.content} for m in messages],
        )
        return str(response.content[0].text).strip()

    def _call_openai(self, messages: list[Message]) -> str:
        api_messages = [{"role": "system", "content": self.system_prompt}]
        api_messages += [{"role": m.role, "content": m.content} for m in messages]
        response = self._client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=api_messages,
        )
        content = response.choices[0].message.content or ""
        return str(content).strip()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, model={self.model!r}, provider={self.provider!r})"
