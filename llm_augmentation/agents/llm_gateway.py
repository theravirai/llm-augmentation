import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]

@dataclass
class LLMResponse:
    content: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    usage: Dict[str, int] = field(default_factory=lambda: {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    })
    raw_response: Dict[str, Any] = field(default_factory=dict)

class LLMGateway:
    """
    Unified LLM Client connecting to OpenAI-compatible endpoints
    (including University of Paderborn AI gateway, OpenAI, Ollama, vLLM).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        default_model: str = "gpt-oss-120b",
        timeout: int = 120
    ):
        # Auto-detect from env or .env file
        self._load_dotenv_if_exists()

        self.base_url = (
            base_url
            or os.environ.get("OPENAI_API_BASE")
            or os.environ.get("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        ).rstrip("/")

        self.api_key = (
            api_key
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")
            or ""
        )
        self.default_model = default_model
        self.timeout = timeout

    def _load_dotenv_if_exists(self):
        env_paths = [
            Path(".env"),
            Path(__file__).resolve().parent.parent.parent / ".env",
            Path("/Volumes/BrainStorm/Github/SootUp-Store/swebench-thesis/.env")
        ]
        for p in env_paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                k, v = line.split("=", 1)
                                k = k.replace("export ", "").strip()
                                v = v.strip().strip("'\"")
                                if k not in os.environ:
                                    os.environ[k] = v
                except Exception:
                    pass

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.0
    ) -> LLMResponse:
        model_name = model or self.default_model

        # Ensure endpoint has standard /v1/chat/completions or /chat/completions
        endpoint = f"{self.base_url}/chat/completions"
        if not self.base_url.endswith("/v1") and "ai-gateway" not in self.base_url:
            endpoint = f"{self.base_url}/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }

        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature
        }

        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": t
                } if "type" not in t else t
                for t in tools
            ]
            payload["tool_choice"] = "auto"

        try:
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            choice = data.get("choices", [{}])[0]
            msg = choice.get("message", {})

            content = msg.get("content")
            tool_calls = []

            if "tool_calls" in msg and msg["tool_calls"]:
                for tc in msg["tool_calls"]:
                    fn = tc.get("function", {})
                    fn_name = fn.get("name", "")
                    fn_args_raw = fn.get("arguments", "{}")
                    try:
                        fn_args = json.loads(fn_args_raw) if isinstance(fn_args_raw, str) else fn_args_raw
                    except json.JSONDecodeError:
                        fn_args = {}
                    tool_calls.append(ToolCall(id=tc.get("id", ""), name=fn_name, arguments=fn_args))

            usage = data.get("usage", {})
            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0)
                },
                raw_response=data
            )

        except Exception as e:
            # Return error representation in LLMResponse
            return LLMResponse(
                content=f"[Error during LLM invocation: {e}]",
                raw_response={"error": str(e)}
            )
