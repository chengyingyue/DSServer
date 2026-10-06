from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_DEEP_PATHS: tuple[str, ...] = ("/chat/completions", "/v1/chat/completions")

DEFAULT_HEADER_WHITELIST: tuple[str, ...] = (
    "user-agent",
    "x-title",
    "x-stainless-lang",
    "x-stainless-package-version",
    "x-stainless-os",
    "x-stainless-arch",
    "x-stainless-runtime",
    "x-stainless-runtime-version",
    "x-stainless-retry-count",
    "content-type",
    "accept",
)


@dataclass
class Config:
    upstream_base_url: str = "https://api.deepseek.com"
    bind: str = "0.0.0.0"
    port: int = 8787
    deep_paths: list[str] = field(default_factory=lambda: list(DEFAULT_DEEP_PATHS))
    store_dir: Path = field(default_factory=lambda: Path("data"))
    keep_raw_sse: bool = True
    header_whitelist: list[str] = field(default_factory=lambda: list(DEFAULT_HEADER_WHITELIST))

    @property
    def log_path(self) -> Path:
        return self.store_dir / "exchanges.jsonl"

    @property
    def conversations_dir(self) -> Path:
        return self.store_dir / "conversations"

    @property
    def index_path(self) -> Path:
        return self.store_dir / "index.md"


def load_config(path: str | Path = "config.toml") -> Config:
    config_path = Path(path)
    if not config_path.exists():
        return Config()
    with config_path.open("rb") as handle:
        data = tomllib.load(handle)
    return Config(
        upstream_base_url=str(data.get("upstream_base_url", Config.upstream_base_url)),
        bind=str(data.get("bind", Config.bind)),
        port=int(data.get("port", Config.port)),
        deep_paths=list(data.get("deep_paths", DEFAULT_DEEP_PATHS)),
        store_dir=Path(data.get("store_dir", "data")),
        keep_raw_sse=bool(data.get("keep_raw_sse", True)),
        header_whitelist=list(data.get("header_whitelist", DEFAULT_HEADER_WHITELIST)),
    )
