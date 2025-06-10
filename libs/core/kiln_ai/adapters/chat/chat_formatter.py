from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Literal, Optional

from kiln_ai.adapters.model_adapters.base_adapter import COT_FINAL_ANSWER_PROMPT


class ChatStrategy(str, Enum):
    """Strategy for how a chat is structured."""

    final_only = "final_only"
    final_and_intermediate = "final_and_intermediate"
    final_and_intermediate_r1_compatible = "final_and_intermediate_r1_compatible"


@dataclass
class ChatMessage:
    role: Literal["system", "assistant", "user"]
    content: Optional[str]


class ChatFormatter(ABC):
    def __init__(
        self,
        system_message: str,
        user_input: str,
        thinking_instructions: str | None = None,
    ) -> None:
        self.system_message = system_message
        self.user_input = user_input
        self.thinking_instructions = thinking_instructions
        self._messages: List[ChatMessage] = []
        self._state = "start"

    @property
    def messages(self) -> List[ChatMessage]:
        return list(self._messages)

    def message_dicts(self) -> List[dict[str, str | None]]:
        return [{"role": m.role, "content": m.content} for m in self._messages]

    @abstractmethod
    def next_turn(
        self, previous_output: str | None = None
    ) -> Optional[List[ChatMessage]]:
        """Advance the conversation and return the next messages if any."""
        raise NotImplementedError


class FinalOnlyFormatter(ChatFormatter):
    def next_turn(
        self, previous_output: str | None = None
    ) -> Optional[List[ChatMessage]]:
        if self._state == "start":
            msgs = [
                ChatMessage("system", self.system_message),
                ChatMessage("user", self.user_input),
            ]
            self._state = "awaiting_final"
            self._messages.extend(msgs)
            return msgs

        if self._state == "awaiting_final":
            if previous_output is None:
                raise ValueError("previous_output required for final step")
            self._messages.append(ChatMessage("assistant", previous_output))
            self._state = "done"
            return None

        return None


class FinalAndIntermediateFormatter(ChatFormatter):
    def __init__(
        self, system_message: str, user_input: str, thinking_instructions: str | None
    ) -> None:
        super().__init__(system_message, user_input, thinking_instructions)
        if self.thinking_instructions is None:
            raise ValueError(
                "thinking_instructions are required when strategy is final_and_intermediate"
            )

    def next_turn(
        self, previous_output: str | None = None
    ) -> Optional[List[ChatMessage]]:
        if self._state == "start":
            msgs = [
                ChatMessage("system", self.system_message),
                ChatMessage("user", self.user_input),
                ChatMessage("user", self.thinking_instructions),
            ]
            self._state = "awaiting_thinking"
            self._messages.extend(msgs)
            return msgs

        if self._state == "awaiting_thinking":
            if previous_output is None:
                raise ValueError("previous_output required for thinking step")
            msgs = [
                ChatMessage("assistant", previous_output),
                ChatMessage("user", COT_FINAL_ANSWER_PROMPT),
            ]
            self._state = "awaiting_final"
            self._messages.extend(msgs)
            return msgs

        if self._state == "awaiting_final":
            if previous_output is None:
                raise ValueError("previous_output required for final step")
            self._messages.append(ChatMessage("assistant", previous_output))
            self._state = "done"
            return None

        return None


class R1Formatter(ChatFormatter):
    def next_turn(
        self, previous_output: str | None = None
    ) -> Optional[List[ChatMessage]]:
        if self._state == "start":
            msgs = [
                ChatMessage("system", self.system_message),
                ChatMessage("user", self.user_input),
            ]
            self._state = "awaiting_final"
            self._messages.extend(msgs)
            return msgs

        if self._state == "awaiting_final":
            if previous_output is None:
                raise ValueError("previous_output required for final step")
            self._messages.append(ChatMessage("assistant", previous_output))
            self._state = "done"
            return None

        return None


def get_chat_formatter(
    *,
    strategy: ChatStrategy,
    system_message: str,
    user_input: str,
    thinking_instructions: str | None = None,
) -> ChatFormatter:
    if strategy == ChatStrategy.final_only:
        return FinalOnlyFormatter(system_message, user_input)
    if strategy == ChatStrategy.final_and_intermediate:
        return FinalAndIntermediateFormatter(
            system_message, user_input, thinking_instructions
        )
    if strategy == ChatStrategy.final_and_intermediate_r1_compatible:
        return R1Formatter(system_message, user_input)

    raise ValueError(f"Unsupported strategy {strategy}")
