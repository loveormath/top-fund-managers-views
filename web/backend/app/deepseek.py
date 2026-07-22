from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek

from .config import AppConfig
from .database import Database, utcnow
from .security import SecretBox


class DeepSeekGateway:
    def __init__(self, config: AppConfig, db: Database, secrets: SecretBox):
        self.config = config
        self.db = db
        self.secrets = secrets

    def set_key(self, api_key: str) -> None:
        self.db.set_setting("deepseek_api_key", self.secrets.encrypt(api_key.strip()))

    def delete_key(self) -> None:
        self.db.delete_setting("deepseek_api_key")

    def get_key(self) -> str | None:
        return self.secrets.decrypt(self.db.get_setting("deepseek_api_key"))

    def masked_key(self) -> str | None:
        return self.secrets.mask(self.get_key())

    async def account_status(self) -> dict[str, Any]:
        api_key = self.get_key()
        if not api_key:
            return {"configured": False, "available": None, "models": [], "balance_infos": []}
        headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
        async with httpx.AsyncClient(base_url=self.config.deepseek_base_url, timeout=20) as client:
            models_response, balance_response = await self._parallel_requests(client, headers)
        models_response.raise_for_status()
        balance_response.raise_for_status()
        models = [item["id"] for item in models_response.json().get("data", [])]
        balance = balance_response.json()
        self.db.set_setting("deepseek_last_checked_at", utcnow())
        return {
            "configured": True,
            "available": balance.get("is_available"),
            "models": models,
            "balance_infos": balance.get("balance_infos", []),
        }

    @staticmethod
    async def _parallel_requests(client: httpx.AsyncClient, headers: dict[str, str]):
        import asyncio

        return await asyncio.gather(
            client.get("/models", headers=headers), client.get("/user/balance", headers=headers)
        )

    def _model(self, temperature: float = 0.15) -> ChatDeepSeek:
        api_key = self.get_key()
        if not api_key:
            raise RuntimeError("尚未配置 DeepSeek API Key")
        return ChatDeepSeek(
            model=self.db.get_setting("model", "deepseek-v4-flash"),
            api_key=api_key,
            api_base=self.config.deepseek_base_url,
            temperature=temperature,
            max_retries=2,
            timeout=150,
        )

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        model = self._model(temperature=0.1)
        response = await model.ainvoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)],
            response_format={"type": "json_object"},
        )
        return self._parse_json(str(response.content))

    async def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        model = self._model(temperature=0.2)
        response = await model.ainvoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        )
        return str(response.content).strip()

    async def generate_text_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        on_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        model = self._model(temperature=0.2)
        pieces: list[str] = []
        async for chunk in model.astream(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        ):
            content = str(chunk.content or "")
            if not content:
                continue
            pieces.append(content)
            if on_delta:
                await on_delta(content)
        return "".join(pieces).strip()

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.S)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, flags=re.S)
            if not match:
                raise ValueError("DeepSeek 未返回有效 JSON")
            return json.loads(match.group(0))
