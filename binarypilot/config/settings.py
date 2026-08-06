"""BinaryPilot application settings — pydantic-settings powered."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh", "max"]

DEFAULT_MAX_TURNS = 500

_BASE_CONFIG = SettingsConfigDict(
    case_sensitive=False,
    populate_by_name=True,
    extra="ignore",
)


def _default_sandbox_image() -> str:
    """The sandbox image tag tracks the installed package version so the CLI
    and the image never drift after upgrades. Falls back to the last known
    good tag if the package metadata isn't readable (editable installs, dev
    checkouts)."""
    try:
        ver = version("binarypilot-agent")
    except PackageNotFoundError:
        ver = "1.5.0"
    return f"ghcr.io/0xida/binarypilot-sandbox:{ver}"


class LlmSettings(BaseSettings):
    model_config = _BASE_CONFIG

    model: str | None = Field(default=None, alias="BINARYPILOT_LLM")
    api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_API_KEY", "OPENAI_API_KEY"),
    )
    api_base: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "LLM_API_BASE",
            "OPENAI_API_BASE",
            "OPENAI_BASE_URL",
            "LITELLM_BASE_URL",
            "OLLAMA_API_BASE",
        ),
    )
    extra_headers: dict[str, str] | None = Field(
        default=None,
        alias="LLM_EXTRA_HEADERS",
    )
    reasoning_effort: ReasoningEffort = Field(default="high", alias="BINARYPILOT_REASONING_EFFORT")
    force_required_tool_choice: bool = Field(
        default=False,
        alias="BINARYPILOT_FORCE_REQUIRED_TOOL_CHOICE",
    )
    prompt_cache: bool = Field(
        default=True,
        alias="BINARYPILOT_PROMPT_CACHE",
    )
    disable_streaming: bool = Field(
        default=False,
        alias="LLM_DISABLE_STREAMING",
    )
    timeout: int = Field(default=300, alias="LLM_TIMEOUT")


class DedupeSettings(BaseSettings):
    model_config = _BASE_CONFIG

    model: str | None = Field(default=None, alias="BINARYPILOT_DEDUPE_MODEL")
    reasoning_effort: ReasoningEffort | None = Field(
        default=None,
        alias="BINARYPILOT_DEDUPE_REASONING_EFFORT",
    )
    api_key: str | None = Field(default=None, alias="DEDUPE_LLM_API_KEY")
    api_base: str | None = Field(default=None, alias="DEDUPE_LLM_API_BASE")
    extra_headers: dict[str, str] | None = Field(
        default=None,
        alias="DEDUPE_LLM_EXTRA_HEADERS",
    )


class ContextSettings(BaseSettings):
    """Context-window management: per-tool-output caps and history compaction."""

    model_config = _BASE_CONFIG

    auto_compact: bool = Field(default=True, alias="BINARYPILOT_CONTEXT_AUTO_COMPACT")
    compact_buffer_tokens: int = Field(
        default=20_000, gt=0, alias="BINARYPILOT_CONTEXT_BUFFER_TOKENS"
    )
    keep_tokens: int = Field(default=8_000, gt=0, alias="BINARYPILOT_CONTEXT_KEEP_TOKENS")
    fallback_context_tokens: int = Field(
        default=200_000, gt=0, alias="BINARYPILOT_CONTEXT_FALLBACK_TOKENS"
    )
    summary_max_tokens: int = Field(default=4_096, gt=0, alias="BINARYPILOT_CONTEXT_SUMMARY_TOKENS")
    tool_output_max_tokens: int = Field(
        default=8_000, gt=0, alias="BINARYPILOT_TOOL_OUTPUT_MAX_TOKENS"
    )
    tool_output_max_lines: int = Field(
        default=2_000, gt=0, alias="BINARYPILOT_TOOL_OUTPUT_MAX_LINES"
    )
    # Floor above the truncation-notice size so a preview always fits.
    tool_output_max_bytes: int = Field(
        default=50 * 1024, ge=1024, alias="BINARYPILOT_TOOL_OUTPUT_MAX_BYTES"
    )


class RuntimeSettings(BaseSettings):
    model_config = _BASE_CONFIG

    image: str = Field(
        default_factory=_default_sandbox_image,
        alias="BINARYPILOT_IMAGE",
    )
    backend: str = Field(default="docker", alias="BINARYPILOT_RUNTIME_BACKEND")
    # Max screenshot/image tool outputs kept live per agent context (0 = none).
    max_context_images: int = Field(default=3, ge=0, alias="BINARYPILOT_MAX_CONTEXT_IMAGES")


class TelemetrySettings(BaseSettings):
    model_config = _BASE_CONFIG

    enabled: bool = Field(default=True, alias="BINARYPILOT_TELEMETRY")


class IntegrationSettings(BaseSettings):
    model_config = _BASE_CONFIG

    perplexity_api_key: str | None = Field(default=None, alias="PERPLEXITY_API_KEY")


class PlatformSettings(BaseSettings):
    """CTF platform credentials (FlagYard / HackTheBox)."""

    model_config = _BASE_CONFIG

    flagyard_username: str | None = Field(default=None, alias="FLAGYARD_USERNAME")
    flagyard_password: str | None = Field(default=None, alias="FLAGYARD_PASSWORD")
    flagyard_access_token: str | None = Field(default=None, alias="FLAGYARD_ACCESS_TOKEN")
    flagyard_api_base: str = Field(
        default="https://api.flagyard.com/api", alias="FLAGYARD_API_BASE"
    )
    htb_token: str | None = Field(default=None, alias="HTB_TOKEN")

    def sandbox_env(self) -> dict[str, str]:
        """Env vars to inject into the sandbox container (set values only)."""
        pairs = {
            "FLAGYARD_USERNAME": self.flagyard_username,
            "FLAGYARD_PASSWORD": self.flagyard_password,
            "FLAGYARD_ACCESS_TOKEN": self.flagyard_access_token,
            "FLAGYARD_API_BASE": self.flagyard_api_base,
            "HTB_TOKEN": self.htb_token,
        }
        return {k: v for k, v in pairs.items() if v}


class ViewerSettings(BaseSettings):
    model_config = _BASE_CONFIG

    # Base URL of the BinaryPilot relay the local viewer proxies to for email
    # verification and encrypted report delivery. The browser never talks to
    # the relay directly; the local server is the only caller.
    app_url: str = Field(default="https://app.binarypilot.local", alias="BINARYPILOT_APP_URL")


class Settings(BaseSettings):
    model_config = _BASE_CONFIG

    llm: LlmSettings = Field(default_factory=LlmSettings)
    dedupe: DedupeSettings = Field(default_factory=DedupeSettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)
    context: ContextSettings = Field(default_factory=ContextSettings)
    telemetry: TelemetrySettings = Field(default_factory=TelemetrySettings)
    integrations: IntegrationSettings = Field(default_factory=IntegrationSettings)
    platforms: PlatformSettings = Field(default_factory=PlatformSettings)
    viewer: ViewerSettings = Field(default_factory=ViewerSettings)
