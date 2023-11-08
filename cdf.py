#!/usr/bin/env python
import difflib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

import typer
from dotenv import load_dotenv
from rich import print
from rich.panel import Panel
from typing_extensions import Annotated

from scripts import bootstrap
from scripts.delete import (
    delete_groups,
    delete_raw,
    delete_timeseries,
    delete_transformations,
)

# from scripts.delete import clean_out_datamodels
from scripts.load import (
    load_datamodel,
    load_groups,
    load_nodes,
    load_raw,
    load_timeseries_metadata,
    load_transformations,
)
from scripts.templates import build_config, read_environ_config
from scripts.utils import CDFToolConfig

app = typer.Typer()
auth_app = typer.Typer()
app.add_typer(auth_app, name="auth")


# These are the supported data types for deploying to a CDF project.
# The enum matches the directory names that are expected in each module directory.
class CDFDataTypes(str, Enum):
    raw = "raw"
    timeseries = "timeseries"
    transformations = "transformations"
    data_models = "data_models"
    instances = "instances"
    groups = "groups"


# Common parameters handled in common callback
@dataclass
class Common:
    override_env: bool
    verbose: bool
    cluster: str
    project: str
    ToolGlobals: CDFToolConfig


@app.callback(invoke_without_command=True)
def common(
    ctx: typer.Context,
    verbose: Annotated[
        bool,
        typer.Option(
            help="Turn on to get more verbose output",
        ),
    ] = False,
    override_env: Annotated[
        bool,
        typer.Option(
            help="Use .env file to override current environment variables",
        ),
    ] = False,
    cluster: Annotated[
        Optional[str],
        typer.Option(
            envvar="CDF_CLUSTER",
            help="Cognite Data Fusion cluster to use",
        ),
    ] = None,
    project: Annotated[
        Optional[str],
        typer.Option(
            envvar="CDF_PROJECT",
            help="Cognite Data Fusion project to use",
        ),
    ] = None,
):
    if ctx.invoked_subcommand is None:
        print(
            "[bold]A tool to manage and deploy Cognite Data Fusion project configurations from the command line or through CI/CD pipelines.[/]"
        )
        print("[bold yellow]Usage:[/] cdf.py [OPTIONS] COMMAND [ARGS]...")
        print("       Use --help for more information.")
        return
    if override_env:
        print("  [bold red]WARNING:[/] Overriding environment variables with values from .env file...")
    load_dotenv(".env", override=override_env)
    # Override cluster and project from the options/env variables
    ToolGlobals = CDFToolConfig(
        client_name="cdf-project-templates",
        cluster=cluster,
        project=project,
    )
    ctx.obj = Common(
        verbose=verbose,
        override_env=override_env,
        cluster=cluster,
        project=project,
        ToolGlobals=ToolGlobals,
    )


@app.command("build")
def build(
    ctx: typer.Context,
    build_dir: Annotated[
        Optional[str],
        typer.Argument(
            help="Where to write the built module files to deploy",
            allow_dash=True,
        ),
    ] = "build",
    build_env: Annotated[
        Optional[str],
        typer.Option(
            "--env",
            "-e",
            help="Build environment to build for",
        ),
    ] = "dev",
    clean: Annotated[
        Optional[bool],
        typer.Option(
            "--clean",
            "-c",
            help="Delete the build directory before building the configurations",
        ),
    ] = True,
) -> None:
    """Build configuration files from the module templates to a local build directory."""
    print(Panel(f"[bold]Building config files from templates into {build_dir} for environment {build_env}...[/bold]"))

    build_config(dir=build_dir, build_env=build_env, clean=clean)


@app.command("deploy")
def deploy(
    ctx: typer.Context,
    build_dir: Annotated[
        Optional[str],
        typer.Argument(
            help="Where to write the built module files to deploy",
            allow_dash=True,
        ),
    ] = "build",
    build_env: Annotated[
        Optional[str],
        typer.Option(
            "--env",
            "-e",
            help="Build environment to build for",
        ),
    ] = "dev",
    interactive: Annotated[
        Optional[bool],
        typer.Option(
            "--interactive",
            "-i",
            help="Whether to use interactive mode when deciding which modules to deploy",
        ),
    ] = False,
    drop: Annotated[
        Optional[bool],
        typer.Option(
            "--drop",
            "-d",
            help="Whether to drop existing configurations, drop per resource if present",
        ),
    ] = True,
    drop_data: Annotated[
        Optional[bool],
        typer.Option(
            "--drop-data",
            "-D",
            help="Whether to drop existing data, drop data if present (WARNING!! includes data from pipelines)",
        ),
    ] = False,
    dry_run: Annotated[
        Optional[bool],
        typer.Option(
            "--dry-run",
            "-r",
            help="Whether to do a dry-run, do dry-run if present",
        ),
    ] = False,
    include: Annotated[
        Optional[List[CDFDataTypes]],
        typer.Option(
            "--include",
            "-i",
            help="Specify which resources to deploy",
        ),
    ] = None,
) -> None:
    """Deploy one or more configuration types from the built configrations to a CDF environment of your choice (as set in local.yaml)."""
    # Set environment variables from local.yaml
    read_environ_config(build_env=build_env)
    if interactive:
        include: CDFDataTypes = []
        mapping = {}
        for i, datatype in enumerate(CDFDataTypes):
            print(f"[bold]{i})[/] {datatype.name}")
            mapping[i] = datatype
        print("\na) All")
        print("q) Quit")
        answer = input("Select data types to deploy: ")
        if answer.casefold() == "a":
            build_dir = "./build"
        elif answer.casefold() == "q":
            exit(0)
        else:
            try:
                include = mapping[int(answer)]
            except ValueError:
                print(f"Invalid selection: {answer}")
                exit(1)
    else:
        if len(include) == 0:
            include = [datatype for datatype in CDFDataTypes]
    print(Panel(f"[bold]Deploying config files from {build_dir} to environment {build_env}...[/]"))
    # Configure a client and load credentials from environment
    build_path = Path(__file__).parent / build_dir
    if not build_path.is_dir():
        alternatives = {
            folder.name: f"{folder.parent.name}/{folder.name}"
            for folder in build_path.parent.iterdir()
            if folder.is_dir()
        }
        matches = difflib.get_close_matches(build_path.name, list(alternatives.keys()), n=3, cutoff=0.3)
        print(
            f"  [bold red]WARNING:[/] {build_dir} does not exists. Did you mean one of these? {[alternatives[m] for m in matches]}"
        )
        exit(1)
    ToolGlobals = ctx.obj.ToolGlobals
    print(ToolGlobals.as_string())
    if CDFDataTypes.raw in include and Path(f"{build_dir}/raw").is_dir():
        # load_raw() will assume that the RAW database name is set like this in the filename:
        # <index>.<raw_db>.<tablename>.csv
        load_raw(
            ToolGlobals,
            raw_db="default",
            drop=drop,
            file=None,
            dry_run=dry_run,
            directory=f"{build_dir}/raw",
        )
        if ToolGlobals.failed:
            print("[bold red]ERROR: [/] Failure to load RAW as expected.")
            exit(1)
    if CDFDataTypes.timeseries in include and Path(f"{build_dir}/timeseries").is_dir():
        load_timeseries_metadata(
            ToolGlobals,
            drop=drop,
            file=None,
            dry_run=dry_run,
            directory=f"{build_dir}/timeseries",
        )
        if ToolGlobals.failed:
            print("[bold red]ERROR: [/] Failure to load timeseries as expected.")
            exit(1)
    if CDFDataTypes.transformations in include and Path(f"{build_dir}/transformations").is_dir():
        load_transformations(
            ToolGlobals,
            file=None,
            drop=drop,
            dry_run=dry_run,
            directory=f"{build_dir}/transformations",
        )
        if ToolGlobals.failed:
            print("[bold red]ERROR: [/] Failure to load transformations as expected.")
            exit(1)
    if CDFDataTypes.data_models in include and (models_dir := Path(f"{build_dir}/data_models")).is_dir():
        load_datamodel(
            ToolGlobals,
            drop=drop,
            directory=models_dir,
            delete_containers=drop_data,  # Also delete properties that have been ingested (leaving empty instances)
            delete_spaces=drop_data,  # Also delete spaces if there are no empty instances (needs to be deleted separately)
            dry_run=dry_run,
        )
        if ToolGlobals.failed:
            print("[bold red]ERROR: [/] Failure to load data models as expected.")
            exit(1)
    if CDFDataTypes.instances in include and (models_dir := Path(f"{build_dir}/data_models")).is_dir():
        load_nodes(
            ToolGlobals,
            directory=models_dir,
            dry_run=dry_run,
        )
        if ToolGlobals.failed:
            print("[bold red]ERROR: [/] Failure to load instances as expected.")
            exit(1)
    if CDFDataTypes.groups in include and Path(f"{build_dir}/auth").is_dir():
        load_groups(
            ToolGlobals,
            directory=f"{build_dir}/auth",
            dry_run=dry_run,
            verbose=ctx.obj.verbose,
        )
    if ToolGlobals.failed:
        print("[bold red]ERROR: [/] Failure to load as expected.")
        exit(1)


@app.command("clean")
def clean(
    ctx: typer.Context,
    build_dir: Annotated[
        Optional[str],
        typer.Argument(
            help="Where to write the built module files to deploy",
            allow_dash=True,
        ),
    ] = "build",
    build_env: Annotated[
        Optional[str],
        typer.Option(
            "--env",
            "-e",
            help="Build environment to build for",
        ),
    ] = "dev",
    dry_run: Annotated[
        Optional[bool],
        typer.Option(
            "--dry-run",
            "-r",
            help="Whether to do a dry-run, do dry-run if present",
        ),
    ] = False,
    include: Annotated[
        Optional[List[CDFDataTypes]],
        typer.Option(
            "--include",
            "-i",
            help="Specify which resources to deploy",
        ),
    ] = None,
) -> None:
    """Clean up a CDF environment as set in local.yaml based on the configuration files in the build directory."""
    if len(include) == 0:
        include = [datatype for datatype in CDFDataTypes]
    print(
        Panel(
            f"[bold]Cleaning configuration in project based on config files from {build_dir} to environment {build_env}...[/]"
        )
    )
    # Set environment variables from local.yaml
    read_environ_config(build_env=build_env)
    # Configure a client and load credentials from environment
    build_path = Path(__file__).parent / build_dir
    if not build_path.is_dir():
        print(f"{build_dir} does not exists.")
        exit(1)
    ToolGlobals = ctx.obj.ToolGlobals
    print("Using following configurations: ")
    print(ToolGlobals)
    if CDFDataTypes.raw in include and Path(f"{build_dir}/raw").is_dir():
        # load_raw() will assume that the RAW database name is set like this in the filename:
        # <index>.<raw_db>.<tablename>.csv
        delete_raw(
            ToolGlobals,
            raw_db="default",
            dry_run=dry_run,
            directory=f"{build_dir}/raw",
        )
    if ToolGlobals.failed:
        print("[bold red]ERROR: [/] Failure to clean raw as expected.")
        exit(1)
    if CDFDataTypes.timeseries in include and Path(f"{build_dir}/timeseries").is_dir():
        delete_timeseries(
            ToolGlobals,
            dry_run=dry_run,
            directory=f"{build_dir}/timeseries",
        )
    if ToolGlobals.failed:
        print("[bold red]ERROR: [/] Failure to clean timeseries as expected.")
        exit(1)
    if CDFDataTypes.transformations in include and Path(f"{build_dir}/transformations").is_dir():
        delete_transformations(
            ToolGlobals,
            dry_run=dry_run,
            directory=f"{build_dir}/transformations",
        )
    if ToolGlobals.failed:
        print("[bold red]ERROR: [/] Failure to clean transformations as expected.")
        exit(1)
    if CDFDataTypes.data_models in include and (models_dir := Path(f"{build_dir}/data_models")).is_dir():
        # We use the load_datamodel with only_drop=True to ensure that we get a clean
        # deletion of the data model entities and instances.
        load_datamodel(
            ToolGlobals,
            drop=True,
            only_drop=True,
            directory=models_dir,
            delete_removed=True,
            delete_spaces=True,  # Also delete properties that have been ingested (leaving empty instances)
            delete_containers=True,  # Also delete spaces if there are no empty instances (needs to be deleted separately)
            dry_run=dry_run,
        )
    if ToolGlobals.failed:
        print("[bold red]ERROR: [/] Failure to delete data models as expected.")
        exit(1)
    if CDFDataTypes.groups in include and Path(f"{build_dir}/auth").is_dir():
        # NOTE! If you want to force deletion of groups that the current running user/service principal
        # is a member of, set my_own=True. This may result in locking out the CI/CD service principal
        # and is thus default not set to True.
        delete_groups(
            ToolGlobals,
            directory=f"{build_dir}/auth",
            my_own=False,
            dry_run=dry_run,
        )
    if ToolGlobals.failed:
        print("[bold red]ERROR: [/] Failure to clean groups as expected.")
        exit(1)


@auth_app.callback(invoke_without_command=True)
def auth_main(ctx: typer.Context):
    """Test, validate, and configure authentication and authorization for CDF projects."""
    if ctx.invoked_subcommand is None:
        print("Use [bold yellow]cdf.py auth --help[/] for more information.")


@auth_app.command("verify")
def auth_verify(
    ctx: typer.Context,
    dry_run: Annotated[
        Optional[bool],
        typer.Option(
            "--dry-run",
            "-r",
            help="Whether to do a dry-run, do dry-run if present",
        ),
    ] = False,
    group_file: Annotated[
        Optional[str],
        typer.Option(
            "--group-file",
            "-f",
            help="Group yaml configuration file to use for group verification",
        ),
    ] = "/common/cdf_auth_readwrite_all/auth/readwrite.all.group.yaml",
    group_id: Annotated[
        Optional[int],
        typer.Option(
            "--group-id",
            "-g",
            help="CDF group id to update with the group configuration specified with --group-file",
        ),
    ] = 0,
    update_group: Annotated[
        Optional[bool],
        typer.Option(
            "--update-group",
            "-u",
            help="Whether to update the group with the group configuration. Can be used instead of --group-id if only one group",
        ),
    ] = False,
):
    """Verify auth capabilities against a group config and
    interactively bootstrap a CDF project with a service account and a user account.

    Needed capabilites for bootstrapping:
    "projectsAcl": ["LIST", "READ"],
    "groupsAcl": ["LIST", "READ", "CREATE", "UPDATE", "DELETE"]

    The default bootstrap group configuration is readwrite.all.group.yaml from the cdf_auth_readwrite_all common module.
    """
    ToolGlobals = ctx.obj.ToolGlobals
    bootstrap.check_auth(
        ToolGlobals,
        group_id=group_id,
        group_file=group_file,
        update_group=update_group,
        dry_run=dry_run,
        verbose=ctx.obj.verbose,
    )


if __name__ == "__main__":
    app()
