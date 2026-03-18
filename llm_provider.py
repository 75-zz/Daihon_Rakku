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

# RunPod Serverless (cloud-hosted local LLM)
# URL format: https://api.runpod.ai/v2/{ENDPOINT_ID}/openai/v1
RUNPOD_TIMEOUT = 600  # RunPodはコールドスタートがあるため長め

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
    """ローカルLLM (llama-server / LM Studio / RunPod Serverless) 用プロバイダー"""

    def __init__(self, base_url: str = LOCAL_LLM_BASE_URL, model: str = LOCAL_LLM_MODEL,
                 api_key: Optional[str] = None):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key  # RunPod認証用（ローカルはNone）
        self._available = None  # lazy check
        # RunPodはコールドスタートがあるためタイムアウトを延長
        self._is_runpod = "runpod.ai" in base_url
        self._timeout = RUNPOD_TIMEOUT if self._is_runpod else LOCAL_LLM_TIMEOUT

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
        messages.append({"role": "user", "content": user + " /no_think"})
        # Assistant prefill: JSONの開始を強制して思考スキップ
        messages.append({"role": "assistant", "content": "{"})

        # max_tokensをローカルLLM向けに制限（context 8192、出力は1024で十分）
        _effective_max_tokens = min(max_tokens, 2048)

        payload = json.dumps({
            "model": self._model,
            "messages": messages,
            "temperature": 0.9,
            "max_tokens": _effective_max_tokens,
        }, ensure_ascii=False).encode("utf-8")

        url = f"{self._base_url}/chat/completions"

        for attempt in range(LOCAL_LLM_MAX_RETRIES + 1):
            try:
                _label = "RunPod" if self._is_runpod else "ローカルLLM"
                if callback:
                    callback(f"  [{_label}] 生成中... (attempt {attempt + 1})")

                headers = {"Content-Type": "application/json; charset=utf-8"}
                if self._api_key:
                    headers["Authorization"] = f"Bearer {self._api_key}"
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers=headers,
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})

                # Assistant prefillの "{" を復元
                if not content.startswith("{"):
                    content = "{" + content

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

            except urllib.error.HTTPError as e:
                _err_body = ""
                try:
                    _err_body = e.read().decode("utf-8", errors="replace")[:500]
                except Exception:
                    pass
                logger.error(f"{_label} HTTP {e.code} (attempt {attempt + 1}): {_err_body}")
                if callback:
                    callback(f"  [{_label}] HTTP {e.code}: {_err_body[:100]}")
                if attempt < LOCAL_LLM_MAX_RETRIES:
                    time.sleep(2 if self._is_runpod else 1)
                    continue
                raise ConnectionError(f"{_label} HTTP {e.code}: {_err_body[:200]}") from e
            except urllib.error.URLError as e:
                logger.error(f"{_label} connection error (attempt {attempt + 1}): {e}")
                if callback:
                    callback(f"  [{_label}] 接続エラー: {e}")
                if attempt < LOCAL_LLM_MAX_RETRIES:
                    time.sleep(3 if self._is_runpod else 2)
                    continue
                raise ConnectionError(f"{_label}に接続できません: {e}") from e
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                _raw = ""
                try:
                    _raw = str(data)[:300] if 'data' in dir() else "no data"
                except Exception:
                    _raw = "could not read data"
                logger.error(f"{_label} parse error (attempt {attempt + 1}): {e} | raw: {_raw}")
                if callback:
                    callback(f"  [{_label}] パースエラー: {e}")
                if attempt < LOCAL_LLM_MAX_RETRIES:
                    time.sleep(1)
                    continue
                raise ValueError(f"{_label}の応答が不正です: {e}") from e

    def is_available(self) -> bool:
        """LLMサーバーが起動しているか確認（ローカル/RunPod共用）"""
        if self._available is not None:
            return self._available
        import urllib.request
        import urllib.error
        try:
            headers = {}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            req = urllib.request.Request(
                f"{self._base_url}/models",
                method="GET",
                headers=headers,
            )
            # RunPodはコールドスタートがあるので長めのタイムアウト
            _check_timeout = 30 if self._is_runpod else 5
            with urllib.request.urlopen(req, timeout=_check_timeout) as resp:
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
        self._max_local_failures = 10  # 連続失敗でローカル無効化（フォールバック込みで余裕を持たせる）

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
    """Qwen3.5の<think>ブロックを除去（インラインthinking含む）"""
    result = _THINK_RE.sub("", text).strip()

    # <think>タグなしのインラインthinkingを処理
    # パターン: 最後の有効なJSONブロックを探す（thinkingの後に最終回答JSONが来る）
    # まず "```json" fenced block を探す
    fence_matches = list(re.finditer(r"```(?:json)?\s*([\s\S]*?)```", result))
    if fence_matches:
        # 最後のfenced blockを使う
        candidate = fence_matches[-1].group(1).strip()
        try:
            json.loads(candidate)
            return candidate
        except (json.JSONDecodeError, ValueError):
            pass

    # Thinking Process: / Thinking: プレフィックスを探す
    for prefix in ["Thinking Process:", "Thinking:", "**Thinking"]:
        if prefix in result:
            # thinkingの後にあるJSON部分を探す
            pass

    # 最後の完全なJSON objectを探す（thinkingの後に来る最終回答）
    last_json = _find_last_complete_json(result)
    if last_json:
        return last_json

    # フォールバック: 最初のJSON部分
    for marker in ["{", "["]:
        idx = result.find(marker)
        if idx > 0:
            result = result[idx:]
            break
    return result


def _find_last_complete_json(text: str) -> Optional[str]:
    """テキストから最も大きい完全なJSONオブジェクトを抽出
    シーンJSONは scene_id/description 等のキーを含む大きなオブジェクト。
    小さい内部オブジェクト（bubbleなど）を誤って拾わないよう、最大サイズを優先する。
    """
    candidates = []

    # 全ての } 位置から逆方向に対応する { を探す
    i = len(text) - 1
    while i >= 0:
        if text[i] == "}":
            close_pos = i
            depth = 0
            for j in range(close_pos, -1, -1):
                if text[j] == "}":
                    depth += 1
                elif text[j] == "{":
                    depth -= 1
                    if depth == 0:
                        candidate = text[j : close_pos + 1]
                        try:
                            parsed = json.loads(candidate)
                            if isinstance(parsed, dict):
                                candidates.append(candidate)
                        except (json.JSONDecodeError, ValueError):
                            pass
                        break
        i -= 1

    if not candidates:
        return None

    # 最大のJSONを優先（シーンJSONは内部のbubbleオブジェクトより大きい）
    # さらに scene_id キーを持つものを最優先
    best = None
    for c in candidates:
        try:
            parsed = json.loads(c)
            if isinstance(parsed, dict) and "scene_id" in parsed:
                if best is None or len(c) > len(best):
                    best = c
        except (json.JSONDecodeError, ValueError):
            pass

    if best:
        return best

    # scene_idが無い場合は最大のJSONを返す
    return max(candidates, key=len)


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
    local_api_key: Optional[str] = None,
) -> HybridRouter:
    """HybridRouterのファクトリ関数

    Args:
        local_base_url: ローカルLLMのURL。RunPodの場合は
            https://api.runpod.ai/v2/{ENDPOINT_ID}/openai/v1
        local_api_key: RunPod API Key（ローカルLM Studioの場合はNone）
    """
    cloud = ClaudeProvider(client, call_claude_func)

    local = None
    if local_enabled:
        local = LocalLLMProvider(base_url=local_base_url, api_key=local_api_key)
        _label = "RunPod" if "runpod.ai" in local_base_url else "ローカルLLM"
        if local.is_available():
            logger.info(f"{_label}検出: {local_base_url}")
        else:
            logger.warning(f"{_label}が応答しません: {local_base_url} → クラウドのみモード")
            local = None

    return HybridRouter(cloud, local)
