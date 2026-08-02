from abc import ABC, abstractmethod
from typing import Any, ClassVar

from textual.widgets import Static


class BaseToolRenderer(ABC):
    tool_name: ClassVar[str] = ""
    css_classes: ClassVar[list[str]] = ["tool-call"]

    @classmethod
    @abstractmethod
    def render(cls, tool_data: dict[str, Any]) -> Static:
        pass

    @classmethod
    def status_icon(cls, status: str) -> tuple[str, str]:
        icons = {
            "running": ("● In progress...", "#f59e0b"),
            "completed": ("✓ Done", "#22c55e"),
            "failed": ("✗ Failed", "#dc2626"),
            "error": ("✗ Error", "#dc2626"),
        }
        return icons.get(status, ("○ Unknown", "dim"))

    @classmethod
    def get_css_classes(cls, status: str) -> str:
        base_classes = cls.css_classes.copy()
        base_classes.append(f"status-{status}")
        return " ".join(base_classes)
