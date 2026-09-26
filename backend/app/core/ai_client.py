"""
统一 AI 客户端 - 支持多模型提供商
支持: OpenAI, DeepSeek, SiliconFlow, 意心(YXAI), 自定义 API
支持从数据库 system_configs 表或配置文件读取配置（数据库优先）

Reason / R1 模型注意：
- 思维链在 reasoning_content，正文在 content；写作只取 content
- 部分网关对 temperature 等参数会 400，需省略
- 多轮勿把 reasoning_content 回传（会 400）
- 推理耗时长，需更长超时
"""

import openai
from app.core.config import get_settings, Settings
from typing import Any, AsyncGenerator, Dict, List, Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import SystemConfig
import json
import re


# 模型名命中则按「推理模式」处理请求参数与响应解析
_REASONING_MODEL_MARKERS = (
    "reasoner",
    "deepseek-r1",
    "/deepseek-r1",
    "deepseek-ai/deepseek-r1",
    "-r1",
    "r1-",
    "qwq",
)

_THINK_BLOCK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)


class _ThinkTagStreamFilter:
    """流式输出中剔除 <think>...</think>（部分 R1 网关把思维链塞进 content）。"""

    _OPEN = "<think>"
    _CLOSE = "</think>"

    def __init__(self) -> None:
        self._buf = ""
        self._in_think = False

    def feed(self, piece: str) -> str:
        if not piece:
            return ""
        self._buf += piece
        out: List[str] = []
        while True:
            if not self._in_think:
                i = self._buf.find(self._OPEN)
                if i >= 0:
                    out.append(self._buf[:i])
                    self._buf = self._buf[i + len(self._OPEN) :]
                    self._in_think = True
                    continue
                # 保留可能未写完的开标签前缀
                hold = self._max_suffix_prefix(self._buf, self._OPEN)
                if hold:
                    out.append(self._buf[:-hold])
                    self._buf = self._buf[-hold:]
                else:
                    out.append(self._buf)
                    self._buf = ""
                break
            j = self._buf.find(self._CLOSE)
            if j >= 0:
                self._buf = self._buf[j + len(self._CLOSE) :]
                self._in_think = False
                continue
            # 保留可能未写完的闭标签前缀，其余丢弃（仍在 think 内）
            hold = self._max_suffix_prefix(self._buf, self._CLOSE)
            self._buf = self._buf[-hold:] if hold else ""
            break
        return "".join(out)

    @staticmethod
    def _max_suffix_prefix(text: str, tag: str) -> int:
        """text 末尾有多长是 tag 的前缀。"""
        max_n = min(len(text), len(tag) - 1)
        for n in range(max_n, 0, -1):
            if tag.startswith(text[-n:]):
                return n
        return 0

    def flush(self) -> str:
        if self._in_think:
            self._buf = ""
            self._in_think = False
            return ""
        rest = self._buf
        self._buf = ""
        return rest


class AIClient:
    """统一的 AI 客户端，支持多个模型提供商"""

    # 数据库配置键名
    CONFIG_KEYS = {
        "provider": "ai_provider",
        "model": "ai_model",
        "api_key": "ai_api_key",
        "base_url": "ai_base_url",
        "temperature": "ai_temperature",
        "max_tokens": "ai_max_tokens",
    }

    def __init__(self, settings: Optional[Settings] = None, db: Optional[Session] = None):
        self.settings = settings or get_settings()
        self._client = None
        self._db = db
        self._init_client()

    def _get_config_from_db(self) -> Optional[dict]:
        """从数据库 system_configs 表获取 AI 配置（可部分字段，用于与 env 合并）"""
        try:
            db = self._db or SessionLocal()
            try:
                configs = {}
                print(f"[AIClient] 正在从数据库读取配置...")
                for key in self.CONFIG_KEYS.values():
                    config_row = db.query(SystemConfig).filter(
                        SystemConfig.config_key == key
                    ).first()
                    if config_row and config_row.config_value:
                        try:
                            value = json.loads(config_row.config_value).get("value")
                        except Exception as e:
                            print(f"[AIClient] 解析 {key} 失败: {e}")
                            value = config_row.config_value
                        # 空字符串视为未设置，继续走 env 回退
                        if value is None or value == "":
                            print(f"[AIClient] DB配置 {key}: 空值，跳过")
                            continue
                        configs[key] = value
                        preview = configs[key]
                        if isinstance(preview, str) and key == "ai_api_key":
                            preview = f"{preview[:8]}..."
                        elif isinstance(preview, str):
                            preview = preview[:40]
                        print(f"[AIClient] DB配置 {key}: {preview}")
                    else:
                        print(f"[AIClient] DB配置 {key}: 未找到")

                if not configs:
                    print(f"[AIClient] 数据库无用户配置，将使用环境变量")
                    return None

                result = {}
                if "ai_provider" in configs:
                    result["provider"] = configs["ai_provider"]
                if "ai_model" in configs:
                    result["model"] = configs["ai_model"]
                if "ai_api_key" in configs:
                    result["api_key"] = configs["ai_api_key"]
                if "ai_base_url" in configs:
                    result["base_url"] = configs["ai_base_url"]
                if "ai_temperature" in configs:
                    result["temperature"] = float(configs["ai_temperature"])
                if "ai_max_tokens" in configs:
                    result["max_tokens"] = int(configs["ai_max_tokens"])

                print(
                    f"[AIClient] DB读取结果: keys={list(result.keys())}, "
                    f"api_key={'已设置' if result.get('api_key') else '未设置'}"
                )
                return result or None
            finally:
                if not self._db:
                    db.close()
        except Exception as e:
            print(f"[AIClient] 从数据库读取配置失败: {e}")
            import traceback
            traceback.print_exc()
        return None

    def _get_config_from_env(self) -> dict:
        """从环境变量/配置文件获取 AI 配置"""
        provider = self.settings.ai_provider

        if provider == "openai":
            api_key = self.settings.openai_api_key
            base_url = self.settings.openai_base_url or "https://api.openai.com/v1"
            model = self.settings.openai_model or "gpt-4"
        elif provider == "deepseek":
            api_key = self.settings.deepseek_api_key
            base_url = self.settings.deepseek_base_url or "https://api.deepseek.com/v1"
            model = self.settings.deepseek_model or "deepseek-chat"
        elif provider == "siliconflow":
            api_key = self.settings.siliconflow_api_key
            base_url = self.settings.siliconflow_base_url or "https://api.siliconflow.cn/v1"
            model = self.settings.siliconflow_model or "deepseek-ai/DeepSeek-V3"
        elif provider == "yxai":
            api_key = self.settings.yxai_api_key
            base_url = self.settings.yxai_base_url or "https://yxai.chat/v1"
            model = self.settings.yxai_model or "deepseek-flash"
        elif provider == "custom":
            api_key = self.settings.custom_api_key
            base_url = self.settings.custom_base_url
            model = self.settings.custom_model
            if not base_url:
                raise ValueError("Custom provider requires custom_base_url")
        else:
            raise ValueError(f"Unknown AI provider: {provider}")

        return {
            "provider": provider,
            "model": model,
            "api_key": api_key,
            "base_url": base_url,
            "temperature": self.settings.ai_temperature,
            "max_tokens": self.settings.ai_max_tokens,
        }

    def _init_client(self):
        """初始化客户端：用户前端配置（DB）优先，未设置字段回退到 env"""
        env_config = self._get_config_from_env()
        db_config = self._get_config_from_db() or {}

        # 逐字段合并：DB 有值则用 DB，否则用 env
        self.provider = db_config.get("provider") or env_config["provider"]
        self.model = db_config.get("model") or env_config["model"]
        self.api_key = db_config.get("api_key") or env_config["api_key"]
        self.base_url = (
            db_config.get("base_url")
            or env_config.get("base_url")
            or self._get_default_base_url(self.provider)
        )
        self.temperature = (
            db_config["temperature"]
            if "temperature" in db_config
            else env_config["temperature"]
        )
        self.max_tokens = (
            db_config["max_tokens"]
            if "max_tokens" in db_config
            else env_config["max_tokens"]
        )

        if db_config.get("api_key"):
            self.config_source = "user"  # 前端保存到 DB 的用户配置
        elif db_config:
            self.config_source = "mixed"  # 部分用户配置 + env
        else:
            self.config_source = "env"

        print(
            f"[AIClient] 配置加载完成: source={self.config_source}, "
            f"provider={self.provider}, model={self.model}, "
            f"api_key_from={'user' if db_config.get('api_key') else 'env'}"
        )

        if not self.api_key or self.api_key == "your-deepseek-api-key":
            print(f"[AIClient] 警告: API Key 未配置或使用的是默认值")

        # 打印诊断信息
        import os
        http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
        https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        print(f"[AIClient] 代理设置: HTTP_PROXY={http_proxy}, HTTPS_PROXY={https_proxy}")
        print(f"[AIClient] 配置源: {self.config_source}")
        print(f"[AIClient] Base URL: {self.base_url}")
        print(f"[AIClient] API Key (前10位): {self.api_key[:10] if self.api_key else 'None'}...")

        # 创建客户端时增加错误处理
        try:
            import os
            ssl_no_verify = os.environ.get('SSL_NO_VERIFY', '').lower() in ('1', 'true', 'yes')
            
            if ssl_no_verify:
                print(f"[AIClient] SSL 验证已禁用")
                import httpx
                import ssl
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                # 长文生成（高 max_tokens）可能超过 60s，与 chat_completion 的 wait_for 对齐
                http_client = httpx.AsyncClient(
                    verify=ssl_context,
                    timeout=300.0,
                )
                
                self._client = openai.AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=300.0,
                    max_retries=1,
                    http_client=http_client,
                )
            else:
                # 使用默认客户端
                self._client = openai.AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=300.0,
                    max_retries=1,
                )
            
            print(f"[AIClient] 客户端创建成功 (SSL验证: {'禁用' if ssl_no_verify else '启用'})")
        except Exception as e:
            print(f"[AIClient] 创建客户端失败: {e}")
            raise

    PROVIDER_TOKEN_LIMITS = {
        "deepseek": 8192,
        "openai": 16384,
        "siliconflow": 8192,
        "yxai": 64000,  # 意心聚合多模型，上下文普遍较大
        "custom": 64000,  # 支持长文本润色，如 Claude 3.5 Sonnet 等
    }

    def _get_default_base_url(self, provider: str) -> str:
        """获取默认的 base_url"""
        urls = {
            "openai": "https://api.openai.com/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "siliconflow": "https://api.siliconflow.cn/v1",
            "yxai": "https://yxai.chat/v1",
            "custom": "",
        }
        return urls.get(provider, "")

    def is_reasoning_model(self, model: Optional[str] = None) -> bool:
        """是否为 DeepSeek Reasoner / R1 等推理模型。"""
        m = (model or self.model or "").lower()
        return any(marker in m for marker in _REASONING_MODEL_MARKERS)

    def _clamp_max_tokens(self, requested: Optional[int]) -> int:
        """将 max_tokens 限制在 provider 允许的范围内。"""
        limit = self.PROVIDER_TOKEN_LIMITS.get(self.provider, 8192)
        val = requested or self.max_tokens
        # reasoner 的 max_tokens 只管最终正文；推理阶段另计，写作场景给足正文额度
        if self.is_reasoning_model():
            val = max(val, 2048)
            limit = min(limit, 8192)
        return min(val, limit)

    @staticmethod
    def _sanitize_messages(messages: list) -> list:
        """去掉历史里的 reasoning_content，避免多轮 400。"""
        cleaned = []
        for msg in messages or []:
            if isinstance(msg, dict):
                cleaned.append(
                    {k: v for k, v in msg.items() if k != "reasoning_content"}
                )
            else:
                cleaned.append(msg)
        return cleaned

    @staticmethod
    def _strip_think_tags(text: str) -> str:
        if not text:
            return ""
        return _THINK_BLOCK_RE.sub("", text).strip()

    @staticmethod
    def _message_content(message: Any) -> str:
        """只取最终正文 content（忽略 reasoning_content）。"""
        if message is None:
            return ""
        content = getattr(message, "content", None)
        if content is None and isinstance(message, dict):
            content = message.get("content")
        text = content if isinstance(content, str) else (str(content) if content else "")
        return AIClient._strip_think_tags(text)

    def _completion_params(
        self,
        messages: list,
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """组装 chat.completions 参数；推理模型省略 temperature 等无效/易报错字段。"""
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": self._sanitize_messages(messages),
            "max_tokens": self._clamp_max_tokens(max_tokens),
            "stream": stream,
        }
        if not self.is_reasoning_model():
            params["temperature"] = (
                temperature if temperature is not None else self.temperature
            )
        else:
            print(
                f"[AIClient] 推理模型 {self.model}：省略 temperature，"
                f"max_tokens={params['max_tokens']}（仅限制正文）"
            )
        if extra:
            # 推理模型禁止调用方强塞 temperature
            if self.is_reasoning_model():
                for k in (
                    "temperature",
                    "top_p",
                    "presence_penalty",
                    "frequency_penalty",
                    "logprobs",
                    "top_logprobs",
                ):
                    extra.pop(k, None)
            params.update(extra)
        return params

    def _check_config(self):
        """检查配置是否有效"""
        print(f"[AIClient] 检查配置: provider={self.provider}, api_key={'已设置' if self.api_key else '未设置'}, base_url={self.base_url}")

        if not self.api_key:
            raise ValueError("API Key 未配置，请先在系统设置中配置 AI 模型")
        if self.api_key == "your-deepseek-api-key":
            raise ValueError("API Key 使用的是默认值 'your-deepseek-api-key'，请配置真实的 API Key")
        if not self.base_url:
            raise ValueError(f"Provider {self.provider} 未配置 base_url")

        # 检查 API Key 格式
        if self.provider == "deepseek" and not self.api_key.startswith("sk-"):
            print(f"[AIClient] 警告: DeepSeek API Key 格式可能不正确，应以 'sk-' 开头")

        print(f"[AIClient] 配置检查通过")

    @property
    def client(self):
        if not self._client:
            self._init_client()
        return self._client

    async def chat_completion(
        self,
        messages: list,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: float = 120.0,
        enable_network_test: bool = True,
        retry_attempts: int = 3,
        **kwargs,
    ) -> str:
        """通用对话接口（非流式）。推理模型只返回最终 content。"""
        import asyncio

        # 检查配置
        self._check_config()

        if self.is_reasoning_model():
            # 推理阶段可能很长，默认超时过短会导致「没生成出字」
            timeout = max(timeout, 300.0)

        # 先测试网络连接（可选；长文本分段场景可关闭以减少延迟）
        if enable_network_test:
            try:
                import httpx
                import ssl
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                test_url = f"{self.base_url}/models"
                async with httpx.AsyncClient(verify=ssl_context, timeout=10.0) as client:
                    headers = {"Authorization": f"Bearer {self.api_key}"}
                    test_response = await client.get(test_url, headers=headers)
                    print(f"[AIClient] 网络测试: {test_url} -> {test_response.status_code}")
                    if test_response.status_code == 401:
                        print(f"[AIClient] 警告: API 返回 401，可能是 API Key 无效")
            except Exception as e:
                print(f"[AIClient] 网络测试失败: {e}")

        # 增加重试机制
        max_retries = max(1, retry_attempts)
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                params = self._completion_params(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                    extra=dict(kwargs) if kwargs else None,
                )
                print(
                    f"[AIClient] 开始调用 AI API (尝试 {attempt}/{max_retries}): "
                    f"model={self.model}, max_tokens={params['max_tokens']}, "
                    f"reasoning={self.is_reasoning_model()}"
                )
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(**params),
                    timeout=timeout,
                )
                choice = response.choices[0] if response.choices else None
                message = choice.message if choice else None
                text = self._message_content(message)
                reasoning = getattr(message, "reasoning_content", None) if message else None
                if reasoning:
                    print(
                        f"[AIClient] 推理模型已产出思维链 "
                        f"({len(reasoning)} 字)，正文 {len(text)} 字"
                    )
                if not text:
                    raise RuntimeError(
                        "模型未返回正文（content 为空）。"
                        "若使用 deepseek-reasoner / R1，请确认网关支持并适当增大 max_tokens。"
                    )
                print(f"[AIClient] AI API 调用成功，正文长度={len(text)}")
                return text
            except asyncio.TimeoutError as e:
                last_error = e
                print(f"[AIClient] 请求超时 (尝试 {attempt}/{max_retries})，将重试...")
                if attempt < max_retries:
                    await asyncio.sleep(5)
            except openai.APIError as e:
                last_error = e
                print(f"[AIClient] API 错误 (尝试 {attempt}/{max_retries}): {e.message}")
                if attempt < max_retries:
                    await asyncio.sleep(5)
            except openai.APIConnectionError as e:
                last_error = e
                print(f"[AIClient] 连接错误 (尝试 {attempt}/{max_retries}): {str(e)[:200]}")
                if attempt < max_retries:
                    await asyncio.sleep(5)
            except RuntimeError as e:
                # 正文为空等业务错误：不重试
                raise Exception(str(e)) from e
            except Exception as e:
                last_error = e
                print(f"[AIClient] 未知错误 (尝试 {attempt}/{max_retries}): {type(e).__name__}: {str(e)[:200]}")
                if attempt < max_retries:
                    await asyncio.sleep(5)

        # 所有重试都失败了
        if isinstance(last_error, asyncio.TimeoutError):
            raise Exception(f"AI 请求超时，请稍后重试\n配置: {self.base_url}\n尝试次数: {max_retries}")
        elif isinstance(last_error, openai.APIError):
            raise Exception(f"AI API 错误: {last_error.message}\n请检查 API Key 是否有效")
        elif isinstance(last_error, openai.APIConnectionError):
            error_detail = str(last_error)
            raise Exception(f"AI 连接失败\nAPI 地址: {self.base_url}\n错误详情: {error_detail[:500]}\n可能原因:\n1. 网络连接问题\n2. 防火墙/代理阻止\n3. VPN 需要开启")
        else:
            raise Exception(f"AI 请求失败: {type(last_error).__name__}: {str(last_error)[:500]}")

    async def stream_completion(
        self, messages: list, temperature: Optional[float] = None, max_tokens: Optional[int] = None,
        timeout: float = 120.0
    ) -> AsyncGenerator[str, None]:
        """流式对话：只推送最终正文；过滤 reasoning_content 与 <think> 块。"""
        import asyncio

        # 检查配置
        self._check_config()

        think_filter = _ThinkTagStreamFilter()
        try:
            params = self._completion_params(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            connect_timeout = 60.0 if self.is_reasoning_model() else 30.0
            stream = await asyncio.wait_for(
                self.client.chat.completions.create(**params),
                timeout=connect_timeout,
            )
            got_content = False
            async for chunk in stream:
                if not getattr(chunk, "choices", None):
                    continue
                delta = chunk.choices[0].delta
                # 推理增量：不写入正文（写作场景）
                _ = getattr(delta, "reasoning_content", None)
                piece = getattr(delta, "content", None)
                if not piece:
                    continue
                cleaned = think_filter.feed(piece)
                if cleaned:
                    got_content = True
                    yield cleaned
            tail = think_filter.flush()
            if tail:
                got_content = True
                yield tail
            if not got_content and self.is_reasoning_model():
                raise Exception(
                    "推理模型流式响应未产生正文。可能仍在思考阶段被中断，或网关只返回了 reasoning_content。"
                )
        except asyncio.TimeoutError:
            raise Exception(f"AI 连接超时\n配置: {self.base_url}\n请检查网络连接")
        except openai.APIError as e:
            raise Exception(f"AI API 错误: {e.message}\n请检查 API Key 是否有效")
        except openai.APIConnectionError as e:
            error_detail = str(e.__cause__) if e.__cause__ else str(e)
            raise Exception(
                f"AI 连接失败\n"
                f"API 地址: {self.base_url}\n"
                f"错误详情: {error_detail}\n"
                f"可能原因:\n"
                f"1. 网络连接问题\n"
                f"2. 防火墙/代理阻止\n"
                f"3. SSL 证书问题\n"
                f"4. VPN 需要开启"
            )
        except openai.AuthenticationError as e:
            raise Exception(f"API Key 无效: {e.message}\n请检查配置的 API Key 是否正确")
        except Exception as e:
            if "推理模型" in str(e) or "未产生正文" in str(e) or "未返回正文" in str(e):
                raise
            raise Exception(f"AI 流式请求失败: {type(e).__name__}: {str(e)}")


# 全局客户端实例（延迟初始化）
_ai_client_instance: AIClient | None = None


def get_ai_client(db: Optional[Session] = None) -> AIClient:
    """获取 AI 客户端实例（延迟初始化，支持数据库优先）"""
    global _ai_client_instance
    if _ai_client_instance is None:
        _ai_client_instance = AIClient(db=db)
    return _ai_client_instance


def refresh_ai_client(db: Optional[Session] = None) -> AIClient:
    """刷新 AI 客户端（在配置更新后调用）"""
    global _ai_client_instance
    _ai_client_instance = AIClient(db=db)
    return _ai_client_instance


# 向后兼容 - 使用属性访问器实现真正的延迟加载
class _LazyAIClient:
    """延迟加载的 AI 客户端代理。

    注意：不要单独缓存实例，必须始终走 get_ai_client()，
    否则 refresh_ai_client() 后业务代码仍会用到旧的 env key。
    """

    def _get_client(self):
        return get_ai_client()

    def __getattr__(self, name):
        return getattr(self._get_client(), name)

    async def chat_completion(self, *args, **kwargs):
        return await self._get_client().chat_completion(*args, **kwargs)

    async def stream_completion(self, *args, **kwargs):
        async for chunk in self._get_client().stream_completion(*args, **kwargs):
            yield chunk


ai_client = _LazyAIClient()
