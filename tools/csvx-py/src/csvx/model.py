"""Public CSVX document model."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Cell:
    value: str | None = None
    dtype: str | None = None
    formula: str | None = None
    annotation: str | None = None
    styles: list[str] = field(default_factory=list)
    comment: str | None = None
    quoted: bool = False


@dataclass(slots=True)
class Sheet:
    name: str
    header: list[Cell] | None = None
    rows: list[list[Cell]] = field(default_factory=list)
    table: dict[str, Any] = field(default_factory=dict)
    columns: list[dict[str, Any]] = field(default_factory=list)

    @property
    def width(self) -> int:
        if self.header is not None:
            return len(self.header)
        if self.columns:
            return len(self.columns)
        return max((len(row) for row in self.rows), default=0)


@dataclass(slots=True)
class Document:
    frontmatter: dict[str, Any] = field(default_factory=dict)
    sheets: list[Sheet] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ConversionIssue:
    feature: str
    message: str
    sheet: str | None = None
    cell: str | None = None
    action: str = "dropped"


@dataclass(slots=True)
class ConversionReport:
    warnings: list[ConversionIssue] = field(default_factory=list)
    losses: list[ConversionIssue] = field(default_factory=list)
    sheets_converted: int = 0

    def add(self, feature: str, message: str, *, sheet: str | None = None,
            cell: str | None = None, action: str = "dropped") -> None:
        self.warnings.append(ConversionIssue(feature, message, sheet, cell, action))
        if action in {"dropped", "changed"}:
            self.losses.append(self.warnings[-1])

    def as_dict(self) -> dict[str, Any]:
        def issue(x: ConversionIssue) -> dict[str, Any]:
            return {"feature": x.feature, "message": x.message, "sheet": x.sheet,
                    "cell": x.cell, "action": x.action}
        return {"sheets_converted": self.sheets_converted,
                "warnings": [issue(x) for x in self.warnings],
                "losses": [issue(x) for x in self.losses]}
