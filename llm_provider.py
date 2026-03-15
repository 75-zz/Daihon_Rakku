"""
LLM Provider Abstraction Layer for Hybrid Local/Cloud Generation

ローカルLLM (HauhauCS/Qwen3.5-35B-A3B) と Claude API のハイブリッドルーティングを提供する。
_call_api() のバックエンドとして動作し、既存パイプラインへの変更を最小限に抑える。

ロールバック: _LOCAL_LLM_ENABLED = False で完全に既存パス（Claude API のみ）に戻る。
"""

import json
import re
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# ============================================================
# Constants
# ============================================================

LOCAL_LLM_BASE_URL = "http://localhost:1234/v1"
LOCAL_LLM_MODEL = "qwen3.5-35b-a3b-uncensored-hauhaucs-aggressive"
LOCAL_LLM_TIMEOUT = 300  # seconds
LOCAL_LLM_MAX_RETRIES = 2

# Thinking block regex (Qwen3.5 outputs <think>...</think>)
_THINK_RE = re.compile(r"<think>[\s\S]*?</think>", re.DOTALL)

# ============================================================
# Provider ABC
# ============================================================

class LLMProvider(ABC):
    """LLM呼び出しの抽象基底クラス"""

    @abstractmethod
    def call(
        self,
        model: str,
        system,
        user: str,
        cost_tracker,
        max_tokens: int = 4096,
        callback: Optional[Callable] = None,
    ) -> str:
        """LLMを呼び出してテキスト応答を返す"""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """プロバイダーが利用可能か確認"""
        ...


# ============================================================
# Claude Provider (既存パスのラッパー)
# ============================================================

class ClaudeProvider(LLMProvider):
    """既存の call_claude() をラップするプロバイダー"""

    def __init__(self, client, call_claude_func):
        self._client = client
        self._call_claude = call_claude_func

    def call(self, model, system, user, cost_tracker, max_tokens=4096, callback=None):
        return self._call_claude(
            self._client, model, system, user, cost_tracker, max_tokens, callback
        )

    def is_available(self) -> bool:
        return self._client is not None


# ============================================================
# Local LLM Provider (OpenAI-compatible)
# ============================================================

class LocalLLMProvider(LLMProvider):
    """ローカルLLM (llama-server / LM Studio) 用プロバイダー"""

    def __init__(self, base_url: str = LOCAL_LLM_BASE_URL, model: str = LOCAL_LLM_MODEL):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._available = None  # lazy check

    def call(self, model, system, user, cost_tracker, max_tokens=4096, callback=None):
        import urllib.request
        import urllib.error

        # Build messages
        messages = []
        if system:
            sys_text = system if isinstance(system, str) else "\n".join(
                b.get("text", "") for b in system if isinstance(b, dict) and b.get("type") == "text"
            )
            messages.append({"role": "system", "content": sys_text})
        messages.append({"role": "user", "content": user})

        payload = json.dumps({
            "model": self._model,
            "messages": messages,
            "temperature": 0.9,
            "max_tokens": max_tokens,
        }, ensure_ascii=False).encode("utf-8")

        url = f"{self._base_url}/chat/completions"

        for attempt in range(LOCAL_LLM_MAX_RETRIES + 1):
            try:
                if callback:
                    callback(f"  [ローカルLLM] 生成中... (attempt {attempt + 1})")

                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json; charset=utf-8"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=LOCAL_LLM_TIMEOUT) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})

                # Strip thinking blocks
                content = _strip_thinking(content)

                # Track cost (local = $0, but track tokens for statistics)
                if cost_tracker:
                    cost_tracker.add(
                        "local-llm",
                        usage.get("prompt_tokens", 0),
                        usage.get("completion_tokens", 0),
                    )

                finish_reason = data["choices"][0].get("finish_reason", "")
                if finish_reason == "length":
                    logger.warning("LocalLLM: output truncated (finish_reason=length)")

                return content

            except urllib.error.URLError as e:
                logger.error(f"LocalLLM connection error (attempt {attempt + 1}): {e}")
                if attempt < LOCAL_LLM_MAX_RETRIES:
                    time.sleep(2)
                    continue
                raise ConnectionError(f"ローカルLLMに接続できません: {e}") from e
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                logger.error(f"LocalLLM response parse error: {e}")
                if attempt < LOCAL_LLM_MAX_RETRIES:
                    time.sleep(1)
                    continue
                raise ValueError(f"ローカルLLMの応答が不正です: {e}") from e

    def is_available(self) -> bool:
        """ローカルLLMサーバーが起動しているか確認"""
        if self._available is not None:
            return self._available
        import urllib.request
        import urllib.error
        try:
            req = urllib.request.Request(
                f"{self._base_url}/models",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self._available = len(data.get("data", [])) > 0
        except (urllib.error.URLError, Exception):
            self._available = False
        return self._available

    def reset_availability(self):
        """可用性キャッシュをリセット（再チェック用）"""
        self._available = None


# ============================================================
# Hybrid Router
# ============================================================

# Routing hints (callsite が指定)
ROUTE_LOCAL_OK = "local_ok"        # ローカルLLMで処理可能
ROUTE_CLOUD_REQUIRED = "cloud"     # クラウド必須
ROUTE_AUTO = "auto"                # intensity等で自動判定

class HybridRouter:
    """ローカル/クラウドのルーティングを管理するルーター"""

    def __init__(self, cloud_provider: ClaudeProvider, local_provider: Optional[LocalLLMProvider] = None):
        self.cloud = cloud_provider
        self.local = local_provider
        self._local_enabled = local_provider is not None
        self._local_failures = 0
        self._max_local_failures = 5  # 連続失敗でローカル無効化

    @property
    def local_enabled(self) -> bool:
        return self._local_enabled and self.local is not None and self.local.is_available()

    def call(
        self,
        model: str,
        system,
        user: str,
        cost_tracker,
        max_tokens: int = 4096,
        callback: Optional[Callable] = None,
        routing_hint: str = ROUTE_AUTO,
    ) -> str:
        """ルーティングルールに基づいてLLM呼び出しを振り分ける"""

        use_local = self._should_use_local(model, routing_hint)

        if use_local:
            try:
                result = self.local.call(model, system, user, cost_tracker, max_tokens, callback)
                self._local_failures = 0  # reset on success
                return result
            except (ConnectionError, ValueError) as e:
                self._local_failures += 1
                logger.warning(
                    f"ローカルLLM失敗 ({self._local_failures}/{self._max_local_failures}): {e}"
                    f" → クラウドにフォールバック"
                )
                if self._local_failures >= self._max_local_failures:
                    logger.error("ローカルLLM連続失敗上限 → ローカル無効化")
                    self._local_enabled = False
                if callback:
                    callback(f"  [フォールバック] ローカル失敗 → クラウドで再生成")
                # Fall through to cloud

        return self.cloud.call(model, system, user, cost_tracker, max_tokens, callback)

    def _should_use_local(self, model: str, routing_hint: str) -> bool:
        """ローカルLLMを使うべきか判定"""
        if not self.local_enabled:
            return False
        if routing_hint == ROUTE_CLOUD_REQUIRED:
            return False
        if routing_hint == ROUTE_LOCAL_OK:
            return True
        # ROUTE_AUTO: model based
        # Sonnet/Opus → cloud, Haiku → local
        if "sonnet" in model or "opus" in model:
            return False
        return True

    def get_stats(self) -> dict:
        """ルーティング統計"""
        return {
            "local_enabled": self._local_enabled,
            "local_available": self.local.is_available() if self.local else False,
            "local_failures": self._local_failures,
        }


# ============================================================
# Utility Functions
# ============================================================

def _strip_thinking(text: str) -> str:
    """Qwen3.5の<think>ブロックを除去"""
    result = _THINK_RE.sub("", text).strip()
    # thinkタグなしでもThinking Process:で始まる場合がある
    if result.startswith("Thinking Process:") or result.startswith("Thinking:"):
        # JSONの開始位置を探す
        for marker in ["{", "["]:
            idx = result.find(marker)
            if idx > 0:
                result = result[idx:]
                break
    return result


def extract_json_from_response(text: str) -> str:
    """応答テキストからJSON部分を抽出（markdown fenceやthinking除去）"""
    text = _strip_thinking(text)

    # ```json ... ``` ブロック抽出
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        return fence_match.group(1).strip()

    # { または [ で始まるJSON部分を抽出
    for marker in ["{", "["]:
        idx = text.find(marker)
        if idx >= 0:
            candidate = text[idx:]
            # 対応する閉じ括弧まで
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                # 末尾から削っていく
                for end_marker in ["}", "]"]:
                    last = candidate.rfind(end_marker)
                    if last > 0:
                        try:
                            json.loads(candidate[: last + 1])
                            return candidate[: last + 1]
                        except json.JSONDecodeError:
                            continue

    return text


def create_hybrid_router(
    client,
    call_claude_func,
    local_enabled: bool = False,
    local_base_url: str = LOCAL_LLM_BASE_URL,
) -> HybridRouter:
    """HybridRouterのファクトリ関数"""
    cloud = ClaudeProvider(client, call_claude_func)

    local = None
    if local_enabled:
        local = LocalLLMProvider(base_url=local_base_url)
        if local.is_available():
            logger.info(f"ローカルLLM検出: {local_base_url}")
        else:
            logger.warning(f"ローカルLLMが応答しません: {local_base_url} → クラウドのみモード")
            local = None

    return HybridRouter(cloud, local)
