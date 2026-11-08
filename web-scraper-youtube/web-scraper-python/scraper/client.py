"""Client responsible for fetching Cafe24 product pages with anti-scraping considerations."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Iterable, Optional

import requests


@dataclass
class RequestConfig:
    base_delay: float = 3.0
    jitter: float = 2.0
    user_agents: Optional[Iterable[str]] = None
    proxy_url: Optional[str] = None


DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/118.0",
]


class Cafe24Client:
    """HTTP client with naive rate limiting and user-agent rotation."""

    def __init__(self, config: RequestConfig) -> None:
        self.config = config

    def fetch(self, url: str) -> requests.Response:
        headers = {"User-Agent": self._choose_user_agent()}
        proxies = {"http": self.config.proxy_url, "https": self.config.proxy_url} if self.config.proxy_url else None
        response = requests.get(url, headers=headers, proxies=proxies, timeout=30)
        self._apply_delay()
        response.raise_for_status()
        return response

    def _choose_user_agent(self) -> str:
        agents = list(self.config.user_agents or DEFAULT_USER_AGENTS)
        return random.choice(agents)

    def _apply_delay(self) -> None:
        delay = self.config.base_delay + random.uniform(0, self.config.jitter)
        time.sleep(delay)
