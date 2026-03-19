from unittest.mock import MagicMock, patch

from adalflow.core.types import ModelType

from api.openai_client import (
    DASHSCOPE_EMBEDDING_SAFE_INPUT_LENGTH,
    OpenAIClient,
)


def _build_client(base_url: str) -> OpenAIClient:
    with patch.object(OpenAIClient, "init_sync_client", return_value=MagicMock()):
        return OpenAIClient(api_key="test-key", base_url=base_url)


def test_dashscope_embedding_input_is_truncated_and_non_empty():
    client = _build_client("https://dashscope.aliyuncs.com/compatible-mode/v1")
    too_long = "x" * 9000

    api_kwargs = client.convert_inputs_to_api_kwargs(
        input=[too_long, "   "],
        model_kwargs={"model": "text-embedding-v4"},
        model_type=ModelType.EMBEDDER,
    )

    assert len(api_kwargs["input"][0]) == DASHSCOPE_EMBEDDING_SAFE_INPUT_LENGTH
    assert api_kwargs["input"][1] == " "


def test_non_dashscope_embedding_input_is_not_truncated():
    client = _build_client("https://api.openai.com/v1")
    too_long = "x" * 9000

    api_kwargs = client.convert_inputs_to_api_kwargs(
        input=[too_long],
        model_kwargs={"model": "text-embedding-3-small"},
        model_type=ModelType.EMBEDDER,
    )

    assert len(api_kwargs["input"][0]) == 9000
