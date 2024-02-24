from __future__ import annotations

import re
from collections import UserDict, UserList
from dataclasses import dataclass

__all__ = ["Variable", "Variables", "Module", "ModuleList"]

from pathlib import Path
from typing import cast

from cognite_toolkit._cdf_tk.load import LOADER_BY_FOLDER_NAME
from cognite_toolkit._cdf_tk.templates import COGNITE_MODULES_PATH
from cognite_toolkit._cdf_tk.templates.data_classes import ConfigEntry, Environment, InitConfigYAML

NOT_SET = object()

_DUMMY_ENVIRONMENT = Environment(
    name="not used",
    project="not used",
    build_type="not used",
    selected_modules_and_packages=[],
    common_function_code="",
)


@dataclass
class Variable:
    name: str
    default: str
    description: str | None = None
    _value: str | object = NOT_SET

    @property
    def value(self) -> str | object:
        if self._value is not NOT_SET:
            return self._value
        return self.default

    @value.setter
    def value(self, value: str) -> None:
        self._value = value

    @classmethod
    def _load(cls, entry: ConfigEntry) -> Variable:
        description: str | None = None
        if entry.default_comment:
            description = "\n".join(entry.default_comment.above) + "\n" + "\n".join(entry.default_comment.after)
        _value: str | object = NOT_SET
        if not (isinstance(entry.default_value, str) and re.match(r"<.*?>", entry.default_value)):
            _value = entry.default_value

        return cls(
            name=entry.key_path[-1],
            _value=_value,
            default=cast(str, entry.default_value),
            description=description,
        )

    def __repr__(self) -> str:
        return f"{type(self).__name__}(value={self.value})"


@dataclass
class Variables(UserDict):
    def __init__(self, collection: dict[str, Variable] | None = None) -> None:
        super().__init__(collection or {})

    @classmethod
    def _load(cls, module_path: Path, default_variables: dict[tuple[str, ...], ConfigEntry]) -> Variables:
        loaded_variables = InitConfigYAML(_DUMMY_ENVIRONMENT).load_variables(module_path)
        variables: dict[str, Variable] = {}
        module_key_path = tuple(module_path.relative_to(COGNITE_MODULES_PATH).parts)
        for key, value in loaded_variables.items():
            *_, variable_name = key
            variable_module_key = [*module_key_path, "first_pop"]
            while variable_module_key:
                variable_module_key.pop()
                key_path = (InitConfigYAML._modules, *variable_module_key, variable_name)
                if default := default_variables.get(key_path):
                    value.default_value = default.default_value
                    value.default_comment = default.default_comment
                    variables[variable_name] = Variable._load(value)
                    break

            else:
                raise ValueError(f"Variable {variable_name} missing from default config in {module_path!r}")

        return cls(variables)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({dict(self)})"


@dataclass(frozen=True)
class Module:
    name: str
    variables: Variables
    resource_types: tuple[str, ...]
    packages: frozenset[str]
    _source: Path
    _readme: str | None = None

    @classmethod
    def _load(
        cls, module_path: Path, packages: frozenset[str], default_variables: dict[tuple[str, ...], ConfigEntry]
    ) -> Module:
        readme: str | None = None
        if (readme_path := module_path / "README.md").exists():
            readme = readme_path.read_text()
        resource_types = tuple(
            resource_path.name for resource_path in module_path.iterdir() if resource_path.name in LOADER_BY_FOLDER_NAME
        )

        return cls(
            name=module_path.name,
            variables=Variables._load(module_path, default_variables),
            resource_types=resource_types,
            packages=packages,
            _source=module_path,
            _readme=readme,
        )


class ModuleList(UserList):
    @property
    def names(self) -> list[str]:
        return [module.name for module in self.data]

    def __getitem__(self, item: str) -> Module:  # type: ignore[override]
        for module in self.data:
            if module.name == item:
                return module
        raise KeyError(f"Module {item!r} not found")
