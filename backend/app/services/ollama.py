import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.schemas import OllamaModel


class OllamaConnectionError(RuntimeError):
    """Raised when the local Ollama service cannot be queried."""


def discover_local_models(base_url: str) -> list[OllamaModel]:
    payload = _get_json(f"{base_url.rstrip('/')}/api/tags")
    models: list[OllamaModel] = []
    for model in payload.get("models", []):
        if model.get("remote_model") or model.get("remote_host"):
            continue
        details = model.get("details") or {}
        models.append(
            OllamaModel(
                name=model["name"],
                size_bytes=int(model.get("size", 0)),
                parameter_size=details.get("parameter_size"),
                capabilities=list(model.get("capabilities") or []),
            )
        )
    return models


def local_model_names(base_url: str) -> set[str]:
    return {model.name for model in discover_local_models(base_url)}


def _get_json(url: str) -> dict:
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=5) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise OllamaConnectionError(f"Unable to query Ollama at {url}: {error}") from error
