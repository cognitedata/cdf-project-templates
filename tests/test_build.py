import re
import sys
from collections.abc import Iterator
from datetime import datetime
from re import Match

import pytest
import yaml
from packaging.version import Version

from cognite_toolkit._version import __version__
from cognite_toolkit.cdf_tk.templates import generate_config
from tests.constants import REPO_ROOT

if sys.version_info >= (3, 11):
    import toml
else:
    import tomli as toml


def test_pyproj_version_matches() -> None:
    version_in_pyproject = toml.loads((REPO_ROOT / "pyproject.toml").read_text())["tool"]["poetry"]["version"]

    assert __version__ == version_in_pyproject, (
        f"Version in 'pyproject.toml' ({version_in_pyproject}) does not match the version in "
        f"cognite_toolkit/_version.py: ({__version__})"
    )


@pytest.mark.parametrize(
    "package_version, changelog_name",
    [(__version__, "CHANGELOG.cdf-tk.md"), (__version__, "CHANGELOG.templates.md")],
)
def test_changelog_entry_version_matches(package_version: str, changelog_name: str) -> None:
    match = next(_parse_changelog(changelog_name))
    changelog_version = match.group(1)
    assert changelog_version == package_version, (
        f"The latest entry in 'CHANGELOG.md' has a different version ({changelog_version}) than "
        f"cognite_toolkit/_version.py: ({__version__}). Did you forgot to add a new entry? "
        "Or maybe you haven't followed the required format?"
    )


@pytest.mark.parametrize(
    "changelog_name",
    [
        "CHANGELOG.cdf-tk.md",
        "CHANGELOG.templates.md",
    ],
)
def test_version_number_is_increasing(changelog_name: str) -> None:
    versions = [Version(match.group(1)) for match in _parse_changelog(changelog_name)]
    for new, old in zip(versions[:-1], versions[1:]):
        if new < old:
            assert False, f"Versions must be strictly increasing: {new} is not higher than the previous, {old}."
    assert True


@pytest.mark.parametrize(
    "changelog_name",
    [
        "CHANGELOG.cdf-tk.md",
        "CHANGELOG.templates.md",
    ],
)
def test_changelog_entry_date(changelog_name: str) -> None:
    match = next(_parse_changelog(changelog_name))
    try:
        datetime.strptime(date := match.group(3), "%Y-%m-%d")
    except Exception:
        assert False, f"Date given in the newest entry in 'CHANGELOG.md', {date!r}, is not valid/parsable (YYYY-MM-DD)"
    else:
        assert True


def test_config_yaml_updated() -> None:
    config_yaml = yaml.safe_load((REPO_ROOT / "cognite_toolkit" / "config.yaml").read_text(encoding="utf-8"))
    expected_config = yaml.safe_load(generate_config(REPO_ROOT / "cognite_toolkit")[0])
    assert config_yaml == expected_config, (
        "The 'config.yaml' file is not up to date with the latest changes. "
        "Please run 'python -m cognite_toolkit.cdf_tk.templates' to update it."
    )


def test_environment_system_variables_updated() -> None:
    environments_yaml = yaml.safe_load(
        (REPO_ROOT / "cognite_toolkit" / "environments.yaml").read_text(encoding="utf-8")
    )
    system_variables = environments_yaml["__system"]

    assert (
        system_variables["cdf_toolkit_version"] == __version__
    ), "The 'cdf_tk_version' system variable is not up to date."


def _parse_changelog(changelog: str) -> Iterator[Match[str]]:
    changelog = (REPO_ROOT / changelog).read_text(encoding="utf-8")
    return re.finditer(r"##\s\[(\d+\.\d+\.\d+(a\d+)?)\]\s-\s(\d+-\d+-\d+)", changelog)
