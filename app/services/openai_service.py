import asyncio
from typing import Optional, Callable, Awaitable, TypeVar
import httpx
from openai import AsyncOpenAI
from app.config import Config
from app.services.logging_service import get_logger
from app.prompts import get_prompts, get_prompt_config

logger = get_logger(__name__)
T = TypeVar("T")


class OpenAIService:
    """Async service for interacting with OpenAI API to generate game content."""
    _http_client: Optional[httpx.AsyncClient] = None
    _client: Optional[AsyncOpenAI] = None

    # ---- Config defaults
    DEFAULT_MODEL = getattr(Config, "OPENAI_MODEL", "gpt-4o-mini")
    TIMEOUT = 30.0

    @classmethod
    async def _ensure_client(cls) -> AsyncOpenAI:
        """Ensure OpenAI client is initialized and return it."""
        if cls._client is not None:
            return cls._client
        
        # Check if API key is available
        if not Config.OPENAI_API_KEY:
            error_msg = "OpenAI API key is not configured. Please set OPENAI_API_KEY environment variable."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Single async HTTP client per process
            cls._http_client = httpx.AsyncClient(
                verify=True,
                timeout=httpx.Timeout(cls.TIMEOUT),
            )
            cls._client = AsyncOpenAI(
                api_key=Config.OPENAI_API_KEY,
                http_client=cls._http_client,
            )
            logger.info("OpenAI client initialized successfully")
            return cls._client
        except Exception as e:
            logger.error(f"Failed to create Async OpenAI client: {e}", exc_info=True)
            raise

    @classmethod
    async def aclose(cls) -> None:
        """Close clients (call on bot shutdown)."""
        try:
            if cls._client is not None:
                # AsyncOpenAI doesn't have a separate close method - close the transport
                cls._client = None
            if cls._http_client is not None:
                await cls._http_client.aclose()
                cls._http_client = None
        except Exception:
            logger.warning("Failed to close HTTP client", exc_info=True)

    @classmethod
    def is_configured(cls) -> bool:
        """Check if the service is properly configured."""
        return bool(Config.OPENAI_API_KEY and Config.OPENAI_API_KEY.strip())

    @classmethod
    def get_config_status(cls) -> dict:
        """Get the current configuration status of the service."""
        quest_config = get_prompt_config("quest")
        world_config = get_prompt_config("world")
        
        return {
            "api_key_configured": bool(Config.OPENAI_API_KEY and Config.OPENAI_API_KEY.strip()),
            "model": cls.DEFAULT_MODEL,
            "timeout": cls.TIMEOUT,
            "max_tokens_quest": quest_config["max_tokens"],
            "max_tokens_world": world_config["max_tokens"],
            "temperature_quest": quest_config["temperature"],
            "temperature_world": world_config["temperature"],
        }

    # ---- Retry helper
    @staticmethod
    async def _with_retries(
        fn: Callable[[], Awaitable[T]],
        attempts: int = 3,
        base_delay: float = 0.5,
    ) -> T:
        """Execute function with exponential backoff retry logic."""
        last_err: Optional[Exception] = None
        for i in range(attempts):
            try:
                return await fn()
            except Exception as e:
                last_err = e
                # Exponential backoff with jitter
                delay = base_delay * (2 ** i)
                await asyncio.sleep(delay)
        assert last_err is not None
        raise last_err

    # ---- Public API
    @classmethod
    async def generate_quest_description(cls, language: str = "en") -> Optional[str]:
        """Generate a fantasy quest description using OpenAI."""
        try:
            client = await cls._ensure_client()
            prompts = get_prompts(language, "quest")
            config = get_prompt_config("quest")

            async def _call():
                resp = await client.chat.completions.create(
                    model=cls.DEFAULT_MODEL,
                    messages=[
                        {"role": "system", "content": prompts["system"]},
                        {"role": "user", "content": prompts["user"]},
                    ],
                    max_tokens=config["max_tokens"],
                    temperature=config["temperature"],
                )
                return resp

            response = await cls._with_retries(_call)
            content = (response.choices[0].message.content or "").strip() if response.choices else ""
            if not content:
                logger.warning("Empty quest description from OpenAI")
                return None

            logger.info(
                "Generated quest description",
                extra={
                    "model": cls.DEFAULT_MODEL,
                    "language": language,
                    "max_tokens": config["max_tokens"],
                    "temperature": config["temperature"],
                },
            )
            return content

        except Exception as e:
            logger.error(
                "Failed to generate quest description",
                exc_info=True,
                extra={"model": cls.DEFAULT_MODEL, "language": language, "error_type": type(e).__name__},
            )
            return None

    @classmethod
    async def generate_world_description(cls, language: str = "en") -> Optional[str]:
        """Generate a fantasy world description using OpenAI."""
        try:
            client = await cls._ensure_client()
            prompts = get_prompts(language, "world")
            config = get_prompt_config("world")

            async def _call():
                resp = await client.chat.completions.create(
                    model=cls.DEFAULT_MODEL,
                    messages=[
                        {"role": "system", "content": prompts["system"]},
                        {"role": "user", "content": prompts["user"]},
                    ],
                    max_tokens=config["max_tokens"],
                    temperature=config["temperature"],
                )
                return resp

            response = await cls._with_retries(_call)
            content = (response.choices[0].message.content or "").strip() if response.choices else ""
            if not content:
                logger.warning("Empty world description from OpenAI")
                return None

            logger.info(
                "Generated world description",
                extra={
                    "model": cls.DEFAULT_MODEL,
                    "language": language,
                    "max_tokens": config["max_tokens"],
                    "temperature": config["temperature"],
                },
            )
            return content

        except Exception as e:
            logger.error(
                "Failed to generate world description",
                exc_info=True,
                extra={"model": cls.DEFAULT_MODEL, "language": language, "error_type": type(e).__name__},
            )
            return None
