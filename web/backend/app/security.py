from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class SecretBox:
    def __init__(self, key_path: Path, configured_key: str | None = None):
        if configured_key:
            key = configured_key.encode("utf-8")
        elif key_path.exists():
            key = key_path.read_bytes().strip()
        else:
            key_path.parent.mkdir(parents=True, exist_ok=True)
            key = Fernet.generate_key()
            key_path.write_bytes(key)
        self.fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self.fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: str | None) -> str | None:
        if not value:
            return None
        try:
            return self.fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("无法解密已保存的 DeepSeek API Key，请重新配置") from exc

    @staticmethod
    def mask(value: str | None) -> str | None:
        if not value:
            return None
        if len(value) <= 8:
            return "•" * len(value)
        return f"{value[:3]}{'•' * 8}{value[-4:]}"
