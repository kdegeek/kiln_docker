"""
# Model Adapters

Model adapters are used to call AI models, like Ollama, OpenAI, etc.

"""

from . import (
    base_adapter,
    openai_model_adapter,
)

__all__ = [
    "base_adapter",
    "openai_model_adapter",
]
