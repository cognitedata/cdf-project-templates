from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from rich import print

from cognite_toolkit._cdf_tk.constants import MODULE_PATH_SEP
from cognite_toolkit._cdf_tk.data_classes._base import ConfigCore, _load_version_variable
from cognite_toolkit._cdf_tk.exceptions import ToolkitMissingModuleError


@dataclass
class SystemYAML(ConfigCore):
    file_name: ClassVar[str] = "_system.yaml"
    cdf_toolkit_version: str
    packages: dict[str, list[str | tuple[str, ...]]] = field(default_factory=dict)

    @classmethod
    def _file_name(cls, build_env_name: str) -> str:
        return cls.file_name

    @classmethod
    def load(cls, data: dict[str, Any], build_env_name: str, filepath: Path) -> SystemYAML:
        version = _load_version_variable(data, filepath.name)
        packages = data.get("packages", {})
        if not packages:
            print(f"  [bold yellow]Warning:[/] No packages defined in {cls.file_name}.")
        return cls(
            filepath=filepath,
            cdf_toolkit_version=version,
            packages={
                name: [
                    tuple([part for part in entry.split(MODULE_PATH_SEP) if part])
                    if MODULE_PATH_SEP in entry
                    else entry
                    for entry in package
                ]
                for name, package in packages.items()
            },
        )

    def validate_modules(
        self, available_modules: set[str | tuple[str, ...]], selected_modules_and_packages: list[str | tuple[str, ...]]
    ) -> None:
        selected_packages = {
            package
            for package in selected_modules_and_packages
            if package in self.packages and isinstance(package, str)
        }
        for package, modules in self.packages.items():
            if package not in selected_packages:
                # We do not check packages that are not selected.
                # Typically, the user will delete the modules that are irrelevant for them;
                # thus we only check the selected packages.
                continue
            if missing := set(modules) - available_modules:
                ToolkitMissingModuleError(
                    f"Package {package} defined in {self.filepath.name!s} is referring "
                    f"the following missing modules {missing}."
                )