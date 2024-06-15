from __future__ import annotations

import shutil
from collections.abc import Iterator, MutableSequence
from pathlib import Path

from packaging.version import Version
from packaging.version import parse as parse_version

from cognite_toolkit._cdf_tk.constants import COGNITE_MODULES
from cognite_toolkit._cdf_tk.data_classes import SystemYAML
from cognite_toolkit._cdf_tk.utils import read_yaml_file
from cognite_toolkit._version import __version__


class Change:
    """A change is a single migration step that can be applied to a project."""

    deprecated_from: Version
    required_from: Version | None = None
    has_file_changes: bool = False

    def __init__(self, project_dir: Path) -> None:
        self._project_path = project_dir

    def do(self) -> set[Path]:
        return set()


class SystemYAMLMoved(Change):
    """The _system.yaml file is now expected to in the root of the project.
    Before it was expected to be in the cognite_modules folder.
    This change moves the file to the root of the project.

    For example:
    Before:
        my_project/
            cognite_modules/
                _system.yaml
    After:
        my_project/
            _system.yaml
    """

    deprecated_from = Version("0.2.0a3")
    required_from = Version("0.2.0a3")
    has_file_changes = True

    def do(self) -> set[Path]:
        system_yaml = self._project_path / COGNITE_MODULES / SystemYAML.file_name
        if not system_yaml.exists():
            return set()
        new_system_yaml = self._project_path / SystemYAML.file_name
        system_yaml.rename(new_system_yaml)
        return {system_yaml}


class RenamedModulesSection(Change):
    """The 'modules' section in the config files has been renamed to 'variables'.
    This change updates the config files to use the new name.

    For example in config.dev.yaml:
    Before:
        ```yaml
            variables:
              cognite_modules:
                cdf_cluster: ${CDF_CLUSTER}
                cicd_clientId: ${IDP_CLIENT_ID}
                cicd_clientSecret: ${IDP_CLIENT_SECRET}
        ```
    After:
        ```yaml
            variables:
              cognite_modules:
                cdf_cluster: ${CDF_CLUSTER}
                cicd_clientId: ${IDP_CLIENT_ID}
                cicd_clientSecret: ${IDP_CLIENT_SECRET}
        ```
    """

    deprecated_from = Version("0.2.0a3")
    required_from = Version("0.2.0a3")
    has_file_changes = True

    def do(self) -> set[Path]:
        changed: set[Path] = set()
        for config_yaml in self._project_path.glob("config.*.yaml"):
            data_raw = config_yaml.read_text()
            # We do not parse the YAML file to avoid removing comments
            updated_file: list[str] = []
            for line in data_raw.splitlines():
                if line.startswith("modules:"):
                    changed.add(config_yaml)
                    updated_file.append(line.replace("modules:", "variables:"))
                else:
                    updated_file.append(line)
            config_yaml.write_text("\n".join(updated_file))
        return changed


class BuildCleanFlag(Change):
    """The `cdf-tk build` command no longer accepts the `--clean` flag.

    The build command now always cleans the build directory before building.
    To avoid cleaning the build directory, you can use the `--no-clean` flag.
    """

    deprecated_from = Version("0.2.0a3")
    required_from = Version("0.2.0a3")
    has_file_changes = False


class CommonFunctionCodeNotSupported(Change):
    """Cognite-Toolkit no longer supports the common functions code."""

    deprecated_from = Version("0.2.0a4")
    required_from = Version("0.2.0a4")
    has_file_changes = True

    def do(self) -> set[Path]:
        # It is complex to move the common functions code, so we will just remove
        # the one module that uses it
        # Todo implement this
        cdf_functions_dummy = self._project_path / "cognite_modules" / "examples" / "cdf_functions_dummy"

        if not cdf_functions_dummy.exists():
            return set()
        shutil.rmtree(cdf_functions_dummy)
        return {cdf_functions_dummy}


class FunctionExternalDataSetIdRenamed(Change):
    """The 'externalDataSetId' field in function YAML files has been renamed to 'dataSetExternalId'.
    This change updates the function YAML files to use the new name.

    The motivation for this change is to make the naming consistent with the rest of the Toolkit.

    For example, in functions/my_function.yaml:

    Before:
        ```yaml
        externalDataSetId: my_external_id
        ```
    After:
        ```yaml
        dataSetExternalId: my_external_id
        ```
    """

    deprecated_from = Version("0.2.0a5")
    required_from = Version("0.2.0a5")
    has_file_changes = True

    def do(self) -> set[Path]:
        changed: set[Path] = set()
        for resource_yaml in self._project_path.glob("*.yaml"):
            if resource_yaml.parent == "functions":
                content = resource_yaml.read_text()
                if "externalDataSetId" in content:
                    changed.add(resource_yaml)
                    content = content.replace("externalDataSetId", "dataSetExternalId")
                    resource_yaml.write_text(content)
        return changed


class ConfigYAMLSelectedRenaming(Change):
    """The 'environment.selected_modules_and_packages' field in the config.yaml files has been
    renamed to 'selected'.
    This change updates the config files to use the new name.

    For example, in config.dev.yaml:

    Before:
        ```yaml
        environment:
          selected_modules_and_packages:
            - my_module
        ```
    After:
        ```yaml
        environment:
          selected:
            - my_module
        ```
    """

    deprecated_from = Version("0.2.0b1")
    has_file_changes = True

    def do(self) -> set[Path]:
        changed = set()
        for config_yaml in self._project_path.glob("config.*.yaml"):
            data = config_yaml.read_text()
            if "selected_modules_and_packages" in data:
                changed.add(config_yaml)
                data = data.replace("selected_modules_and_packages", "selected")
                config_yaml.write_text(data)
        return changed


class RequiredFunctionLocation(Change):
    """Function Resource YAML files are now expected to be in the 'functions' folder.
    Before they could be in subfolders inside the 'functions' folder.

    This change moves the function YAML files to the 'functions' folder.

    For example:
    Before:
        modules/
          my_module/
              functions/
                some_subdirectory/
                    my_function.yaml
    After:
        modules/
          my_module/
              functions/
                my_function.yaml
    """

    deprecated_from = Version("0.2.0b3")
    required_from = Version("0.2.0b3")
    has_file_changes = True

    def do(self) -> set[Path]:
        changed = set()
        for resource_yaml in self._project_path.glob("functions/**/*.yaml"):
            if self._is_function(resource_yaml):
                new_path = self._new_path(resource_yaml)
                if new_path != resource_yaml:
                    resource_yaml.rename(new_path)
                    changed.add(new_path)
        return changed

    @staticmethod
    def _is_function(resource_yaml: Path) -> bool:
        # Functions require a 'name' field and to distinguish from a FunctionSchedule
        # we check that the 'cronExpression' field is not present
        parsed = read_yaml_file(resource_yaml)
        if isinstance(parsed, dict):
            return "name" in parsed and "cronExpression" not in parsed
        elif isinstance(parsed, list):
            return all("name" in item and "cronExpression" not in item for item in parsed)
        return False

    @staticmethod
    def _new_path(resource_yaml: Path) -> Path:
        # Search the path for the 'functions' folder and move the file there
        for parent in resource_yaml.parents:
            if parent.name == "functions":
                return parent / resource_yaml.name
        return resource_yaml


class UpdateModuleVersion(Change):
    """In the _system.yaml file, the 'cdf_toolkit_version' field has been updated to the same version as the CLI.

    This change updates the 'cdf_toolkit_version' field in the _system.yaml file to the same version as the CLI.

    For example, in _system.yaml:
    Before:
        ```yaml
        cdf_toolkit_version: {module_version}
        ```
    After:
        ```yaml
        cdf_toolkit_version: {cli_version}
        ```
    """

    deprecated_from = parse_version(__version__)
    required_from = parse_version(__version__)
    has_file_changes = True

    def do(self) -> set[Path]:
        system_yaml = self._project_path / SystemYAML.file_name
        if not system_yaml.exists():
            return set()
        raw = system_yaml.read_text()
        new_system_yaml = []
        changes: set[Path] = set()
        # We do not parse the YAML file to avoid removing comments
        for line in raw.splitlines():
            if line.startswith("cdf_toolkit_version:"):
                new_system_yaml.append(f"cdf_toolkit_version: {__version__}")
                changes.add(system_yaml)
            else:
                new_system_yaml.append(line)
        system_yaml.write_text("\n".join(new_system_yaml))
        return changes


_CHANGES: list[type[Change]] = [change for change in Change.__subclasses__()]


class Changes(list, MutableSequence[Change]):
    @classmethod
    def load(cls, module_version: Version, project_path: Path) -> Changes:
        return cls([change(project_path) for change in _CHANGES if change.deprecated_from >= module_version])

    @property
    def required_changes(self) -> Changes:
        return Changes([change for change in self if change.required_from is not None])

    @property
    def optional_changes(self) -> Changes:
        return Changes([change for change in self if change.required_from is None])

    def __iter__(self) -> Iterator[Change]:
        return super().__iter__()