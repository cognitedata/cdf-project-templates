from __future__ import annotations

import dataclasses
import itertools
from abc import ABC
from collections import UserList
from collections.abc import Collection
from dataclasses import dataclass
from enum import Enum
from functools import total_ordering
from typing import Any, Generic, List, TypeVar, Union


class SeverityLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@total_ordering
@dataclass(frozen=True)
class ToolkitWarning(ABC):
    def group_key(self) -> tuple[Any, ...]:
        """This is used to group warnings together when printing them out."""
        return (type(self).__name__,)

    def group_header(self) -> str:
        """This can be overridden to provide a custom header for a group of warnings."""
        return f"    {type(self).__name__}:"

    def as_tuple(self) -> tuple[Any, ...]:
        return type(self).__name__, *dataclasses.astuple(self)

    def __lt__(self, other: ToolkitWarning) -> bool:
        if not isinstance(other, ToolkitWarning):
            return NotImplemented
        return self.as_tuple() < other.as_tuple()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ToolkitWarning):
            return NotImplemented
        return self.as_tuple() == other.as_tuple()


T_Warning = TypeVar("T_Warning", bound=ToolkitWarning)


class WarningList(UserList, Generic[T_Warning]):
    def __init__(self, collection: Collection[T_Warning] | None = None) -> None:
        super().__init__(collection or [])

    def __str__(self) -> str:
        output = [""]
        for group_key, group in itertools.groupby(sorted(self), key=lambda w: w.group_key()):
            group_list = list(group)
            header = group_list[0].group_header()
            if header:
                output.append(header)
            for warning in group_list:
                output.append(f"{'    ' * 2} * {warning!s}")
        return "\n".join(output)


@dataclass(frozen=True)
class GeneralWarning(ToolkitWarning):
    severity: SeverityLevel = SeverityLevel.MEDIUM
    message: str | None = None
    details: Union[None, str, List[str]] = None  # Allow None, str, list[str]

    def __str__(self) -> str:
        output = [f"    [bold yellow]WARNING:[/]{type(self).__name__}: {self.message}"]

        if self.details:
            if isinstance(self.details, str):
                output.append(f"{'    ' * 2}{self.details}")
            else:
                for detail in self.details:
                    output.append(f"{'    ' * 2}{detail}")
        return "\n".join(output)


@dataclass(frozen=True)
class ToolkitCleanDependenciesIncludedWarning(GeneralWarning):
    severity: SeverityLevel = SeverityLevel.MEDIUM

    def __init__(self) -> None:
        super().__init__(message="Some resources were added due to dependencies.", details=None)


@dataclass(frozen=True)
class ToolkitCleanDatasetNotSupportedWarning(GeneralWarning):
    severity: SeverityLevel = SeverityLevel.LOW

    def __init__(self) -> None:
        super().__init__(message="Dataset cleaning is not supported, skipping...", details=None)
