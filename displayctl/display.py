from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional
import hashlib


@dataclass
class Display:
    name: str
    edid_name: str = ""
    connected: bool = False
    primary: bool = False
    active: bool = False
    width: int = 0
    height: int = 0
    refresh: float = 0.0
    offset_x: int = 0
    offset_y: int = 0
    rotation: str = "normal"
    edid_hash: str = ""
    modes: list[dict] = field(default_factory=list)

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}" if self.width and self.height else ""

    @property
    def position(self) -> str:
        return f"{self.offset_x}x{self.offset_y}" if self.connected else ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> Display:
        return Display(**{k: v for k, v in data.items() if k in Display.__dataclass_fields__})

    @staticmethod
    def compute_edid_hash(edid_bytes: bytes) -> str:
        return hashlib.sha256(edid_bytes).hexdigest()[:16]

    def fingerprint(self) -> str:
        if self.edid_hash:
            return self.edid_hash
        if self.edid_name:
            return hashlib.md5(self.edid_name.encode()).hexdigest()[:16]
        return hashlib.md5(self.name.encode()).hexdigest()[:16]
