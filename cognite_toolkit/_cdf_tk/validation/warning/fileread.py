from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._base import ToolkitWarning


@dataclass(frozen=True)
class FileReadWarning(ToolkitWarning, ABC):
    filepath: Path
    id_value: str
    id_name: str


@dataclass(frozen=True)
class SnakeCaseWarning(FileReadWarning):
    actual: str
    expected: str

    def group_key(self) -> tuple[Any, ...]:
        return self.filepath, self.id_value, self.id_name

    def group_header(self) -> str:
        return f"    In File {str(self.filepath)!r}\n    In entry {self.id_name}={self.id_value!r}"

    def __str__(self) -> str:
        return f"CaseWarning: Got {self.actual!r}. Did you mean {self.expected!r}?"


@dataclass(frozen=True)
class TemplateVariableWarning(FileReadWarning):
    path: str

    def group_key(self) -> tuple[Any, ...]:
        return (self.path,)

    def group_header(self) -> str:
        return f"    In Section {str(self.path)!r}"

    def __str__(self) -> str:
        return f"{type(self).__name__}: Variable {self.id_name!r} has value {self.id_value!r} in file: {self.filepath.name}. Did you forget to change it?"


@dataclass(frozen=True)
class DataSetMissingWarning(FileReadWarning):
    resource_name: str

    def group_key(self) -> tuple[Any, ...]:
        return (self.filepath,)

    def group_header(self) -> str:
        return f"    In File {str(self.filepath)!r}"

    def __str__(self) -> str:
        # Avoid circular import
        from cognite_toolkit._cdf_tk.load import TransformationLoader

        if self.filepath.parent.name == TransformationLoader.folder_name:
            return f"{type(self).__name__}: It is recommended to use a data set if source or destination can be scoped with a data set. If not, ignore this warning."
        else:
            return f"{type(self).__name__}: It is recommended that you set dataSetExternalId for {self.resource_name}. This is missing in {self.filepath.name}. Did you forget to add it?"
