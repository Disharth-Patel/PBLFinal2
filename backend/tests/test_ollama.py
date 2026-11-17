from unittest.mock import patch

from app.services.ollama import discover_local_models, local_model_names


def test_discovery_excludes_remote_models() -> None:
    payload = {
        "models": [
            {
                "name": "qwen2.5:1.5b-instruct",
                "size": 123,
                "details": {"parameter_size": "1.5B"},
                "capabilities": ["completion"],
            },
            {
                "name": "glm-5.1:cloud",
                "size": 1,
                "remote_model": "glm-5.1",
                "remote_host": "https://ollama.com",
            },
        ]
    }
    with patch("app.services.ollama._get_json", return_value=payload):
        models = discover_local_models("http://localhost:11434")

    assert [model.name for model in models] == ["qwen2.5:1.5b-instruct"]


def test_local_model_names_are_explicitly_whitelisted() -> None:
    with patch(
        "app.services.ollama._get_json",
        return_value={"models": [{"name": "local:latest", "size": 1, "details": {}}]},
    ):
        assert local_model_names("http://localhost:11434") == {"local:latest"}
