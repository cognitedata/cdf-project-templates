import traceback
from graphlib import TopologicalSorter
from pathlib import Path

import typer
from cognite.client.data_classes._base import T_CogniteResourceList
from cognite.client.exceptions import CogniteAPIError, CogniteNotFoundError
from cognite.client.utils.useful_types import SequenceNotStr
from rich import print
from rich.panel import Panel

from cognite_toolkit._cdf_tk.commands._base import LoaderCommand
from cognite_toolkit._cdf_tk.exceptions import (
    ToolkitCleanResourceError,
    ToolkitNotADirectoryError,
)
from cognite_toolkit._cdf_tk.load import (
    LOADER_BY_FOLDER_NAME,
    AuthLoader,
    DataSetsLoader,
    DeployResults,
    ResourceContainerLoader,
    ResourceLoader,
)
from cognite_toolkit._cdf_tk.load._base_loaders import T_ID
from cognite_toolkit._cdf_tk.load.data_classes import ResourceContainerDeployResult, ResourceDeployResult
from cognite_toolkit._cdf_tk.templates import (
    BUILD_ENVIRONMENT_FILE,
)
from cognite_toolkit._cdf_tk.templates.data_classes import (
    BuildEnvironment,
)
from cognite_toolkit._cdf_tk.tk_warnings import (
    ToolkitDependenciesIncludedWarning,
    ToolkitNotSupportedWarning,
)
from cognite_toolkit._cdf_tk.utils import (
    CDFToolConfig,
    read_yaml_file,
)


class CleanCommand(LoaderCommand):
    def execute(
        self, ctx: typer.Context, build_dir: str, build_env_name: str, dry_run: bool, include: list[str]
    ) -> None:
        ToolGlobals = CDFToolConfig.from_context(ctx)

        build_ = BuildEnvironment.load(
            read_yaml_file(Path(build_dir) / BUILD_ENVIRONMENT_FILE), build_env_name, "clean"
        )
        build_.set_environment_variables()

        Panel(f"[bold]Cleaning environment {build_env_name} based on config files from {build_dir}...[/]")
        build_path = Path(build_dir)
        if not build_path.is_dir():
            raise ToolkitNotADirectoryError(f"'{build_dir}'. Did you forget to run `cdf-tk build` first?")

        # The 'auth' loader is excluded, as it is run at the end.
        selected_loaders = {
            loader_cls: loader_cls.dependencies
            for folder_name, loader_classes in LOADER_BY_FOLDER_NAME.items()
            if folder_name in include and folder_name != "auth" and (build_path / folder_name).is_dir()
            for loader_cls in loader_classes
        }

        print(ToolGlobals.as_string())
        if ToolGlobals.failed:
            raise ToolkitCleanResourceError("Failure to delete data models as expected.")

        results = DeployResults([], "clean", dry_run=dry_run)
        resolved_list = list(TopologicalSorter(selected_loaders).static_order())
        if len(resolved_list) > len(selected_loaders):
            dependencies = [item.folder_name for item in resolved_list if item not in selected_loaders]
            self.warn(ToolkitDependenciesIncludedWarning(dependencies=dependencies))
        for loader_cls in reversed(resolved_list):
            if not issubclass(loader_cls, ResourceLoader):
                continue
            loader = loader_cls.create_loader(ToolGlobals)
            if type(loader) is DataSetsLoader:
                self.warn(ToolkitNotSupportedWarning(feature="Dataset clean."))
                continue
            result = loader.clean_resources(
                build_path / loader_cls.folder_name,
                ToolGlobals,
                drop=True,
                dry_run=dry_run,
                drop_data=True,
                verbose=ctx.obj.verbose,
            )
            if result:
                results[result.name] = result
            if ToolGlobals.failed:
                if results and results.has_counts:
                    print(results.counts_table())
                if results and results.has_uploads:
                    print(results.uploads_table())
                raise ToolkitCleanResourceError(f"Failure to clean {loader_cls.folder_name} as expected.")

        if "auth" in include and (directory := (Path(build_dir) / "auth")).is_dir():
            result = AuthLoader.create_loader(ToolGlobals, target_scopes="all").clean_resources(
                directory,
                ToolGlobals,
                drop=True,
                dry_run=dry_run,
                verbose=ctx.obj.verbose,
            )
            if ToolGlobals.failed:
                raise ToolkitCleanResourceError("Failure to clean auth as expected.")
            if result:
                results[result.name] = result
        if results.has_counts:
            print(results.counts_table())
        if results.has_uploads:
            print(results.uploads_table())
        if ToolGlobals.failed:
            raise ToolkitCleanResourceError("Failure to clean auth as expected.")

    def clean_resources(
        self,
        loader: ResourceLoader,
        path: Path,
        ToolGlobals: CDFToolConfig,
        dry_run: bool = False,
        drop: bool = True,
        drop_data: bool = False,
        verbose: bool = False,
    ) -> ResourceDeployResult | None:
        if not isinstance(loader, ResourceContainerLoader) and not drop:
            # Skipping silently as this, we will not drop data or delete this resource
            return ResourceDeployResult(name=loader.display_name)
        if not loader.support_drop:
            print(f"  [bold green]INFO:[/] {loader.display_name!r} cleaning is not supported, skipping...")
            return ResourceDeployResult(name=loader.display_name)
        elif isinstance(loader, ResourceContainerLoader) and not drop_data:
            print(
                f"  [bold]INFO:[/] Skipping cleaning of {loader.display_name!r}. This is a data resource (it contains "
                f"data and is not only configuration/metadata) and therefore "
                "requires the --drop-data flag to be set to perform cleaning..."
            )
            return ResourceContainerDeployResult(name=loader.display_name, item_name=loader.item_name)

        filepaths = loader.find_files(path)

        # Since we do a clean, we do not want to verify that everything exists wrt data sets, spaces etc.
        loaded_resources = self._load_files(loader, filepaths, ToolGlobals, skip_validation=True, verbose=verbose)
        if loaded_resources is None:
            ToolGlobals.failed = True
            return None

        # Duplicates should be handled on the build step,
        # but in case any of them slip through, we do it here as well to
        # avoid an error.
        loaded_resources, duplicates = self._remove_duplicates(loaded_resources, loader)

        capabilities = loader.get_required_capability(loaded_resources)
        if capabilities:
            ToolGlobals.verify_capabilities(capabilities)

        nr_of_items = len(loaded_resources)
        if nr_of_items == 0:
            return ResourceDeployResult(name=loader.display_name)

        existing_resources = loader.retrieve(loader.get_ids(loaded_resources)).as_write()
        nr_of_existing = len(existing_resources)

        if drop:
            prefix = "Would clean" if dry_run else "Cleaning"
            with_data = "with data " if isinstance(loader, ResourceContainerLoader) else ""
        else:
            prefix = "Would drop data from" if dry_run else "Dropping data from"
            with_data = ""
        print(f"[bold]{prefix} {nr_of_existing} {loader.display_name} {with_data}from CDF...[/]")
        for duplicate in duplicates:
            print(f"  [bold yellow]WARNING:[/] Skipping duplicate {loader.display_name} {duplicate}.")

        # Deleting resources.
        if isinstance(loader, ResourceContainerLoader) and drop_data:
            nr_of_dropped_datapoints = self._drop_data(existing_resources, loader, dry_run, verbose)
            if drop:
                nr_of_deleted = self._delete_resources(existing_resources, loader, dry_run, verbose)
            else:
                nr_of_deleted = 0
            if verbose:
                print("")
            return ResourceContainerDeployResult(
                name=loader.display_name,
                deleted=nr_of_deleted,
                total=nr_of_items,
                dropped_datapoints=nr_of_dropped_datapoints,
                item_name=loader.item_name,
            )
        elif not isinstance(self, ResourceContainerLoader) and drop:
            nr_of_deleted = self._delete_resources(existing_resources, loader, dry_run, verbose)
            if verbose:
                print("")
            return ResourceDeployResult(name=loader.display_name, deleted=nr_of_deleted, total=nr_of_items)
        else:
            return ResourceDeployResult(name=loader.display_name)

    def _delete_resources(
        self, loaded_resources: T_CogniteResourceList, loader: ResourceLoader, dry_run: bool, verbose: bool
    ) -> int:
        nr_of_deleted = 0
        resource_ids = loader.get_ids(loaded_resources)
        if dry_run:
            nr_of_deleted += len(resource_ids)
            if verbose:
                print(f"  Would have deleted {self._print_ids_or_length(resource_ids)}.")
            return nr_of_deleted

        try:
            nr_of_deleted += loader.delete(resource_ids)
        except CogniteAPIError as e:
            print(f"  [bold yellow]WARNING:[/] Failed to delete {self._print_ids_or_length(resource_ids)}. Error {e}.")
            if verbose:
                print(Panel(traceback.format_exc()))
        except CogniteNotFoundError:
            if verbose:
                print(f"  [bold]INFO:[/] {self._print_ids_or_length(resource_ids)} do(es) not exist.")
        except Exception as e:
            print(f"  [bold yellow]WARNING:[/] Failed to delete {self._print_ids_or_length(resource_ids)}. Error {e}.")
            if verbose:
                print(Panel(traceback.format_exc()))
        else:  # Delete succeeded
            if verbose:
                print(f"  Deleted {self._print_ids_or_length(resource_ids)}.")
        return nr_of_deleted

    def _drop_data(
        self, loaded_resources: T_CogniteResourceList, loader: ResourceContainerLoader, dry_run: bool, verbose: bool
    ) -> int:
        nr_of_dropped = 0
        resource_ids = loader.get_ids(loaded_resources)
        if dry_run:
            resource_drop_count = loader.count(resource_ids)
            nr_of_dropped += resource_drop_count
            if verbose:
                self._verbose_print_drop(resource_drop_count, resource_ids, loader, dry_run)
            return nr_of_dropped

        try:
            resource_drop_count = loader.drop_data(resource_ids)
            nr_of_dropped += resource_drop_count
        except CogniteAPIError as e:
            if e.code == 404 and verbose:
                print(f"  [bold]INFO:[/] {len(resource_ids)} {loader.display_name} do(es) not exist.")
        except CogniteNotFoundError:
            return nr_of_dropped
        except Exception as e:
            print(
                f"  [bold yellow]WARNING:[/] Failed to drop {loader.item_name} from {len(resource_ids)} {loader.display_name}. Error {e}."
            )
            if verbose:
                print(Panel(traceback.format_exc()))
        else:  # Delete succeeded
            if verbose:
                self._verbose_print_drop(resource_drop_count, resource_ids, loader, dry_run)
        return nr_of_dropped

    def _verbose_print_drop(
        self, drop_count: int, resource_ids: SequenceNotStr[T_ID], loader: ResourceContainerLoader, dry_run: bool
    ) -> None:
        prefix = "Would have dropped" if dry_run else "Dropped"
        if drop_count > 0:
            print(
                f"  {prefix} {drop_count:,} {loader.item_name} from {loader.display_name}: "
                f"{self._print_ids_or_length(resource_ids)}."
            )
        elif drop_count == 0:
            verb = "is" if len(resource_ids) == 1 else "are"
            print(
                f"  The {loader.display_name}: {self._print_ids_or_length(resource_ids)} {verb} empty, "
                f"thus no {loader.item_name} will be {'touched' if dry_run else 'dropped'}."
            )
        else:
            # Count is not supported
            print(
                f" {prefix} all {loader.item_name} from {loader.display_name}: "
                f"{self._print_ids_or_length(resource_ids)}."
            )
