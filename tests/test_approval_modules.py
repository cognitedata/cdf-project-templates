"""
Approval test takes a snapshot of the results and then compare them to last run, ref https://approvaltests.com/,
and fails if they have changed.

If the changes are desired, you can update the snapshot by running `pytest --force-regen`.
"""
from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Literal
from unittest.mock import MagicMock

import pytest
import typer
from pytest import MonkeyPatch

from cognite_toolkit import _version
from cognite_toolkit.cdf import Common, build, clean, deploy, main_init
from cognite_toolkit.cdf_tk.templates import COGNITE_MODULES, iterate_modules, read_yaml_file
from cognite_toolkit.cdf_tk.utils import CDFToolConfig
from tests.conftest import ApprovalCogniteClient

REPO_ROOT = Path(__file__).parent.parent

SNAPSHOTS_DIR = REPO_ROOT / "tests" / "test_approval_modules_snapshots"
SNAPSHOTS_DIR.mkdir(exist_ok=True)
SNAPSHOTS_DIR_CLEAN = REPO_ROOT / "tests" / "test_approval_modules_snapshots_clean"
SNAPSHOTS_DIR_CLEAN.mkdir(exist_ok=True)


@contextlib.contextmanager
def chdir(new_dir: Path) -> Iterator[None]:
    """
    Change directory to new_dir and return to the original directory when exiting the context.

    Args:
        new_dir: The new directory to change to.

    """
    current_working_dir = Path.cwd()
    os.chdir(new_dir)

    try:
        yield

    finally:
        os.chdir(current_working_dir)


def find_all_modules() -> Iterator[Path]:
    for module, _ in iterate_modules(REPO_ROOT / "cognite_toolkit" / COGNITE_MODULES):
        yield pytest.param(module, id=f"{module.parent.name}/{module.name}")


@pytest.fixture
def local_tmp_path():
    return SNAPSHOTS_DIR.parent / "tmp"


@pytest.fixture
def local_tmp_project_path(local_tmp_path: Path):
    project_path = SNAPSHOTS_DIR.parent / "pytest-project"
    project_path.mkdir(exist_ok=True)
    return project_path


@pytest.fixture
def cdf_tool_config(cognite_client_approval: ApprovalCogniteClient, monkeypatch: MonkeyPatch) -> CDFToolConfig:
    monkeypatch.setenv("CDF_PROJECT", "pytest-project")
    monkeypatch.setenv("IDP_TOKEN_URL", "dummy")
    monkeypatch.setenv("IDP_CLIENT_ID", "dummy")
    monkeypatch.setenv("IDP_CLIENT_SECRET", "dummy")

    with chdir(REPO_ROOT):
        # Build must always be executed from root of the project
        cdf_tool = MagicMock(spec=CDFToolConfig)
        cdf_tool.verify_client.return_value = cognite_client_approval.mock_client
        cdf_tool.verify_capabilities.return_value = cognite_client_approval.mock_client
        cdf_tool.failed = False

        cdf_tool.verify_dataset.return_value = 42
        cdf_tool.data_set_id = 999
        yield cdf_tool


@pytest.fixture
def typer_context(cdf_tool_config: CDFToolConfig) -> typer.Context:
    context = MagicMock(spec=typer.Context)
    context.obj = Common(
        verbose=False,
        override_env=True,
        cluster="pytest",
        project="pytest-project",
        mockToolGlobals=cdf_tool_config,
    )
    return context


def mock_read_yaml_file(module_path: Path, monkeypatch: MonkeyPatch) -> None:
    def fake_read_yaml_file(
        filepath: Path, expected_output: Literal["list", "dict"] = "dict"
    ) -> dict[str, Any] | list[dict[str, Any]]:
        if filepath.name == "environments.yaml":
            return {
                "dev": {"project": "pytest-project", "type": "dev", "deploy": [module_path.name]},
                "__system": {"cdf_toolkit_version": _version.__version__},
            }
        return read_yaml_file(filepath, expected_output)

    monkeypatch.setattr("cognite_toolkit.cdf_tk.templates.read_yaml_file", fake_read_yaml_file)
    monkeypatch.setattr("cognite_toolkit.cdf.read_yaml_file", fake_read_yaml_file)


@pytest.fixture
def init_project(typer_context: typer.Context, local_tmp_project_path: Path) -> None:
    main_init(
        typer_context,
        dry_run=False,
        upgrade=False,
        git=None,
        init_dir=str(local_tmp_project_path),
        no_backup=True,
        clean=True,
    )
    return None


@pytest.mark.parametrize("module_path", list(find_all_modules()))
def test_deploy_module_approval(
    module_path: Path,
    local_tmp_path: Path,
    local_tmp_project_path: Path,
    monkeypatch: MonkeyPatch,
    cognite_client_approval: ApprovalCogniteClient,
    cdf_tool_config: CDFToolConfig,
    typer_context: typer.Context,
    init_project: None,
    data_regression,
) -> None:
    mock_read_yaml_file(module_path, monkeypatch)

    build(
        typer_context,
        source_dir=str(local_tmp_project_path),
        build_dir=str(local_tmp_path),
        build_env="dev",
        clean=True,
    )
    deploy(
        typer_context,
        build_dir=str(local_tmp_path),
        build_env="dev",
        interactive=False,
        drop=True,
        dry_run=False,
        include=[],
    )

    not_mocked = cognite_client_approval.not_mocked_calls()
    assert not not_mocked, (
        f"The following APIs have been called without being mocked: {not_mocked}, "
        "Please update the list _API_RESOURCES in tests/conftest.py"
    )

    dump = cognite_client_approval.dump()
    data_regression.check(dump, fullpath=SNAPSHOTS_DIR / f"{module_path.name}.yaml")

    for group_calls in cognite_client_approval.auth_create_group_calls():
        lost_capabilities = group_calls.capabilities_all_calls - group_calls.last_created_capabilities
        assert (
            not lost_capabilities
        ), f"The group {group_calls.name!r} has lost the capabilities: {', '.join(lost_capabilities)}"


@pytest.mark.parametrize("module_path", list(find_all_modules()))
def test_deploy_dry_run_module_approval(
    module_path: Path,
    local_tmp_path: Path,
    local_tmp_project_path: Path,
    monkeypatch: MonkeyPatch,
    cognite_client_approval: ApprovalCogniteClient,
    cdf_tool_config: CDFToolConfig,
    typer_context: typer.Context,
    init_project: None,
) -> None:
    mock_read_yaml_file(module_path, monkeypatch)

    build(
        typer_context,
        source_dir=str(local_tmp_project_path),
        build_dir=str(local_tmp_path),
        build_env="dev",
        clean=True,
    )
    deploy(
        typer_context,
        build_dir=str(local_tmp_path),
        build_env="dev",
        interactive=False,
        drop=True,
        dry_run=True,
        include=[],
    )

    assert not (
        calls := cognite_client_approval.create_calls()
    ), f"No resources should be created in dry run: got these calls: {calls}"
    assert not (
        calls := cognite_client_approval.delete_calls()
    ), f"No resources should be deleted in dry run: got these calls: {calls}"
    assert cdf_tool_config.verify_dataset.call_count == 0, "Dataset should not be checked in dry run"
    assert cdf_tool_config.verify_spaces.call_count == 0, "Spaces should not be checked in dry run"
    assert (
        cdf_tool_config.verify_extraction_pipeline.call_count == 0
    ), "Extraction pipelines should not be checked in dry run"


@pytest.mark.parametrize("module_path", list(find_all_modules()))
def test_clean_module_approval(
    module_path: Path,
    local_tmp_path: Path,
    local_tmp_project_path: Path,
    monkeypatch: MonkeyPatch,
    cognite_client_approval: ApprovalCogniteClient,
    cdf_tool_config: CDFToolConfig,
    typer_context: typer.Context,
    data_regression,
) -> None:
    mock_read_yaml_file(module_path, monkeypatch)

    main_init(
        typer_context,
        dry_run=False,
        upgrade=False,
        git=None,
        init_dir=str(local_tmp_project_path),
        no_backup=True,
        clean=True,
    )

    build(
        typer_context,
        source_dir=str(local_tmp_project_path),
        build_dir=str(local_tmp_path),
        build_env="dev",
        clean=True,
    )
    clean(
        typer_context,
        build_dir=str(local_tmp_path),
        build_env="dev",
        interactive=False,
        dry_run=False,
        include=[],
    )

    not_mocked = cognite_client_approval.not_mocked_calls()
    assert not not_mocked, (
        f"The following APIs have been called without being mocked: {not_mocked}, "
        "Please update the list _API_RESOURCES in tests/conftest.py"
    )
    dump = cognite_client_approval.dump()
    data_regression.check(dump, fullpath=SNAPSHOTS_DIR_CLEAN / f"{module_path.name}.yaml")
