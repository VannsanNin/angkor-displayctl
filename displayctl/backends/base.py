from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
from displayctl.display import Display


class DisplayBackend(ABC):
    @abstractmethod
    def get_displays(self) -> list[Display]:
        ...

    @abstractmethod
    def mirror(self, dry_run: bool = False, verbose: bool = False) -> None:
        ...

    @abstractmethod
    def extend(self, dry_run: bool = False, verbose: bool = False,
               primary: Optional[str] = None, arrange: str = "left-right") -> None:
        ...

    @abstractmethod
    def second_only(self, dry_run: bool = False, verbose: bool = False) -> None:
        ...

    @abstractmethod
    def pc_only(self, dry_run: bool = False, verbose: bool = False) -> None:
        ...

    @abstractmethod
    def set_mode(self, mode: str, primary: Optional[str] = None,
                 arrange: str = "left-right",
                 dry_run: bool = False, verbose: bool = False) -> None:
        ...

    @abstractmethod
    def set_brightness(self, value: int, display: Optional[str] = None,
                       dry_run: bool = False, verbose: bool = False) -> None:
        ...

    @abstractmethod
    def set_resolution(self, resolution: str, display: str,
                       dry_run: bool = False, verbose: bool = False) -> None:
        ...

    @abstractmethod
    def set_refresh(self, refresh: int, display: str,
                    dry_run: bool = False, verbose: bool = False) -> None:
        ...

    @abstractmethod
    def set_rotation(self, rotation: str, display: str,
                     dry_run: bool = False, verbose: bool = False) -> None:
        ...

    @abstractmethod
    def get_active_mode(self) -> str:
        ...
