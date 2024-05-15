from __future__ import annotations

import dataclasses
import itertools
from abc import ABC, abstractmethod
from collections import UserList
from collections.abc import Collection
from dataclasses import dataclass
from enum import Enum
from functools import total_ordering
from typing import Any, ClassVar, Generic, TypeVar, Union

RICH_WARNING_FORMAT = "    [bold yellow]WARNING:[/] "
RICH_WARNING_DETAIL_FORMAT = f"{'    ' * 2}"


class SeverityLevel(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SeverityFormat:
    @staticmethod
    def get_rich_severity_format(severity: SeverityLevel, *messages: str) -> str:
        if severity == SeverityLevel.HIGH:
            return f"[bold red]WARNING:[/][{severity.value}] {' '.join(messages)}"
        elif severity == SeverityLevel.MEDIUM:
            return f"[bold yellow]WARNING:[/][{severity.value}] {' '.join(messages)}"
        elif severity == SeverityLevel.LOW:
            return f"[bold green]WARNING:[/][{severity.value}] {' '.join(messages)}"
        else:
            return f"[bold yellow]WARNING {' '.join(messages)}[/]"

    @staticmethod
    def get_rich_detail_format(message: str) -> str:
        return f"{'    ' * 2}{message}"


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

    @abstractmethod
    def get_message(self) -> str:
        raise NotImplementedError()


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
class GeneralWarning(ToolkitWarning, ABC):
    severity: ClassVar[SeverityLevel]
    message: ClassVar[str | None] = None


@dataclass(frozen=True)
class UnexpectedFileLocationWarning(ToolkitWarning):
    severity: ClassVar[SeverityLevel] = SeverityLevel.LOW
    filepath: str
    alternative: str

    def get_message(self) -> str:
        message = f"{self.filepath!r} does not exist. Using {self.alternative!r} instead."
        return SeverityFormat.get_rich_severity_format(self.severity, message)


@dataclass(frozen=True)
class ToolkitBugWarning(ToolkitWarning):
    severity: ClassVar[SeverityLevel] = SeverityLevel.HIGH
    message: ClassVar[str] = "Please contact the toolkit maintainers with the error message and traceback:"
    header: str
    traceback: str

    def get_message(self) -> str:
        return SeverityFormat.get_rich_severity_format(self.severity, self.header, self.message, self.traceback)


@dataclass(frozen=True)
class IncorrectResourceWarning(ToolkitWarning):
    severity: ClassVar[SeverityLevel] = SeverityLevel.LOW
    message: ClassVar[str] = "The resource not semantically correct:"
    location: str
    resource: str
    details: str | list[str] | None = None

    def get_message(self) -> str:
        extra_details = []
        if self.details:
            if isinstance(self.details, str):
                extra_details.append(self.details)
            else:
                extra_details.extend(self.details)
        return SeverityFormat.get_rich_severity_format(
            self.severity, self.location, self.message, self.resource, *extra_details
        )


@dataclass(frozen=True)
class LowSeverityWarning(GeneralWarning):
    severity: ClassVar[SeverityLevel] = SeverityLevel.LOW
    message_raw: str

    def get_message(self) -> str:
        return SeverityFormat.get_rich_severity_format(self.severity, self.message_raw)


@dataclass(frozen=True)
class MediumSeverityWarning(GeneralWarning):
    severity: ClassVar[SeverityLevel] = SeverityLevel.MEDIUM
    message_raw: str

    def get_message(self) -> str:
        return SeverityFormat.get_rich_severity_format(self.severity, self.message_raw)


@dataclass(frozen=True)
class HighSeverityWarning(GeneralWarning):
    severity: ClassVar[SeverityLevel] = SeverityLevel.HIGH
    message_raw: str

    def get_message(self) -> str:
        return SeverityFormat.get_rich_severity_format(self.severity, self.message_raw)


@dataclass(frozen=True)
class ToolkitDependenciesIncludedWarning(GeneralWarning):
    severity: ClassVar[SeverityLevel] = SeverityLevel.LOW
    message: ClassVar[str] = "Some resources were added due to dependencies."
    dependencies: Union[None, str, list[str]]

    def get_message(self) -> str:
        output = [SeverityFormat.get_rich_severity_format(self.severity, self.message)]

        if self.dependencies:
            if isinstance(self.dependencies, str):
                output.append(SeverityFormat.get_rich_detail_format(self.dependencies))
            else:
                for dependency in self.dependencies:
                    output.append(SeverityFormat.get_rich_detail_format(dependency))
        return "\n".join(output)


@dataclass(frozen=True)
class ToolkitNotSupportedWarning(GeneralWarning):
    severity: ClassVar[SeverityLevel] = SeverityLevel.LOW
    message: ClassVar[str] = "This feature is not supported"
    feature: str

    details: str | list[str] | None = None

    def get_message(self) -> str:
        extra_details = []
        if self.details:
            if isinstance(self.details, str):
                extra_details.append(self.details)
            else:
                extra_details.extend(self.details)
        return SeverityFormat.get_rich_severity_format(self.severity, self.message, self.feature, *extra_details)