import pytest

from kiln_ai.adapters.chat import ChatStrategy, get_chat_formatter
from kiln_ai.adapters.fine_tune.dataset_formatter import (
    ModelTrainingData,
    generate_chat_message_response,
)
from kiln_ai.adapters.model_adapters.base_adapter import COT_FINAL_ANSWER_PROMPT


def test_chat_formatter_final_only():
    training_data = ModelTrainingData(
        input="test input",
        system_message="system message",
        final_output="test output",
    )
    expected = generate_chat_message_response(training_data)["messages"]

    formatter = get_chat_formatter(
        strategy=ChatStrategy.final_only,
        system_message="system message",
        user_input="test input",
    )

    first = formatter.next_turn()
    assert [m.__dict__ for m in first] == expected[:2]

    assert formatter.next_turn("test output") is None
    assert formatter.message_dicts() == expected


def test_chat_formatter_final_and_intermediate():
    training_data = ModelTrainingData(
        input="test input",
        system_message="system message",
        final_output="test output",
        thinking="thinking output",
        thinking_instructions="thinking instructions",
        thinking_final_answer_prompt=COT_FINAL_ANSWER_PROMPT,
    )
    expected = generate_chat_message_response(training_data)["messages"]

    formatter = get_chat_formatter(
        strategy=ChatStrategy.final_and_intermediate,
        system_message="system message",
        user_input="test input",
        thinking_instructions="thinking instructions",
    )

    first = formatter.next_turn()
    assert [m.__dict__ for m in first] == expected[:3]

    second = formatter.next_turn("thinking output")
    assert [m.__dict__ for m in second] == expected[3:5]

    assert formatter.next_turn("test output") is None
    assert formatter.message_dicts() == expected


def test_chat_formatter_r1_style():
    training_data = ModelTrainingData(
        input="test input",
        system_message="system message",
        final_output="test output",
        thinking="thinking output",
        thinking_instructions=None,
        thinking_final_answer_prompt=None,
        thinking_r1_style=True,
    )
    expected = generate_chat_message_response(training_data)["messages"]
    combined = expected[-1]["content"]

    formatter = get_chat_formatter(
        strategy=ChatStrategy.final_and_intermediate_r1_compatible,
        system_message="system message",
        user_input="test input",
    )

    first = formatter.next_turn()
    assert [m.__dict__ for m in first] == expected[:2]

    assert formatter.next_turn(combined) is None
    assert formatter.message_dicts() == expected
