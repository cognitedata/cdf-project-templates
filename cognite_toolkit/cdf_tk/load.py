# Copyright 2023 Cognite AS
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import io
import os
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar, Union

import pandas as pd
from cognite.client import CogniteClient
from cognite.client.data_classes import (
    OidcCredentials,
    Transformation,
    TransformationList,
)
from cognite.client.data_classes._base import (
    CogniteResource,
    CogniteResourceList,
)
from cognite.client.data_classes.capabilities import (
    Capability,
    GroupsAcl,
    RawAcl,
    TimeSeriesAcl,
    TransformationsAcl,
)
from cognite.client.data_classes.data_modeling import (
    ContainerApply,
    DataModelApply,
    NodeApply,
    NodeApplyList,
    NodeOrEdgeData,
    SpaceApply,
    ViewApply,
    ViewId,
)
from cognite.client.data_classes.iam import Group, GroupList
from cognite.client.data_classes.time_series import TimeSeries, TimeSeriesList
from cognite.client.exceptions import CogniteAPIError
from rich import print

from .delete import delete_instances
from .utils import CDFToolConfig, load_yaml_inject_variables


@dataclass
class Difference:
    added: list[CogniteResource]
    removed: list[CogniteResource]
    changed: list[CogniteResource]
    unchanged: list[CogniteResource]

    def __iter__(self):
        return iter([self.added, self.removed, self.changed, self.unchanged])

    def __next__(self):
        return next([self.added, self.removed, self.changed, self.unchanged])


T_ID = TypeVar("T_ID", bound=Union[str, int])
T_Resource = TypeVar("T_Resource", bound=Union[CogniteResource, pd.DataFrame])
T_ResourceList = TypeVar("T_ResourceList", bound=Union[CogniteResourceList, list[pd.DataFrame]])


class Loader(ABC, Generic[T_ID, T_Resource, T_ResourceList]):
    load_files_individually: bool = False
    filetypes = frozenset({"yaml", "yml"})
    parent_name: str = ""
    name: str
    resource_cls: type[CogniteResource]
    list_cls: type[CogniteResourceList]
    actions: frozenset[Capability.Action]
    acl: type[Capability]

    def __init__(self, client: CogniteClient):
        self.client = client
        if self.parent_name:
            parent = getattr(client, self.parent_name)
        else:
            parent = client
        self.api_class = getattr(parent, self.name)

    @classmethod
    def create_loader(cls, ToolGlobals: CDFToolConfig):
        client = ToolGlobals.verify_client(capabilities=[cls.actions])
        return cls(client)

    @classmethod
    @abstractmethod
    def get_id(cls, item: T_Resource) -> T_ID:
        raise NotImplementedError

    # Default implementations that can be overridden
    def create(self, items: T_Resource | Sequence[T_Resource]) -> T_Resource | T_ResourceList | None:
        return self.api_class.create(items)

    def delete(self, ids: T_ID | Sequence[T_ID]) -> T_ResourceList:
        return self.api_class.delete(ids)

    def retrieve(self, ids: T_ID) -> T_Resource | T_ResourceList | None:
        return self.api_class.retrieve(ids)

    def load_file(self, filepath: Path, ToolGlobals: CDFToolConfig) -> T_ResourceList:
        return self.list_cls.load(load_yaml_inject_variables(filepath, ToolGlobals.environment_variables()))


class TimeSeriesLoader(Loader[str, TimeSeries, TimeSeriesList]):
    name = "time_series"
    resource_cls = TimeSeries
    list_cls = TimeSeriesList
    actions = frozenset({TimeSeriesAcl.Action.Read, TimeSeriesAcl.Action.Write})
    acl = TimeSeriesAcl

    def get_id(self, item: TimeSeries) -> str:
        return item.external_id


class TransformationLoader(Loader[str, Transformation, TransformationList]):
    name = "transformations"
    resource_cls = Transformation
    list_cls = TransformationList
    actions = frozenset({TransformationsAcl.Action.Read, TransformationsAcl.Action.Write})
    acl = TransformationsAcl

    def get_id(self, item: Transformation) -> str:
        return item.external_id

    def load_file(self, filepath: Path, ToolGlobals: CDFToolConfig) -> TransformationList:
        raw = load_yaml_inject_variables(filepath, ToolGlobals.environment_variables())
        # The `authentication` key is custom for this template:
        source_oidc_credentials = raw.get("authentication", {}).get("read") or raw.get("authentication") or {}
        destination_oidc_credentials = raw.get("authentication", {}).get("write") or raw.get("authentication") or {}
        transformation = Transformation.load(raw)
        transformation.source_oidc_credentials = source_oidc_credentials and OidcCredentials.load(
            source_oidc_credentials
        )
        transformation.destination_oidc_credentials = destination_oidc_credentials and OidcCredentials.load(
            destination_oidc_credentials
        )
        sql_file = filepath.parent / f"{transformation.external_id}.sql"
        if not sql_file.exists():
            raise FileNotFoundError(
                f"Could not find sql file {sql_file.name}. Expected to find it next to the yaml config file."
            )
        transformation.query = sql_file.read_text()
        transformation.data_set_id = ToolGlobals.data_set_id
        return self.list_cls([transformation])

    def create(self, items: Transformation | Sequence[Transformation]) -> Transformation | TransformationList | None:
        created = self.client.transformations.create(items)
        for t in items if isinstance(items, Sequence) else [items]:
            if t.schedule.interval != "":
                t.schedule.external_id = t.external_id
                self.client.transformations.schedules.create(t.schedule)
        return created


class GroupLoader(Loader[int, Group, GroupList]):
    name = "groups"
    parent_name = "iam"
    resource_cls = Group
    list_cls = GroupList
    actions = frozenset(
        {GroupsAcl.Action.Read, GroupsAcl.Action.List, GroupsAcl.Action.Create, GroupsAcl.Action.Delete}
    )
    capability = GroupsAcl

    @classmethod
    def get_id(cls, item: Group) -> int:
        return item.id

    def load_file(self, filepath: Path, ToolGlobals: CDFToolConfig) -> GroupList:
        raw = load_yaml_inject_variables(filepath, ToolGlobals.environment_variables())
        for capability in raw.get("capabilities", []):
            for _, values in capability.items():
                if len(values.get("scope", {}).get("datasetScope", {}).get("ids", [])) > 0:
                    values["scope"]["datasetScope"]["ids"] = [
                        ToolGlobals.verify_dataset(ext_id)
                        for ext_id in values.get("scope", {}).get("datasetScope", {}).get("ids", [])
                    ]
        return GroupList([Group.load(raw)])

    def create(self, items: Group | Sequence[GroupLoader]) -> Group | GroupLoader | None:
        created = self.client.iam.groups.create(items)
        old_groups = self.client.iam.groups.list(all=True).data
        created_names = {g.name for g in created}
        to_delete = [g.id for g in old_groups if g.name in created_names]
        self.client.iam.groups.delete(to_delete)
        return created


class DatapointsLoader(Loader[str, pd.DataFrame, list[pd.DataFrame]]):
    load_files_individually = True
    name = "datapoints"
    resource_cls = pd.DataFrame
    actions = frozenset({TimeSeriesAcl.Action.Read, TimeSeriesAcl.Action.Write})
    capability = TimeSeriesAcl

    @classmethod
    def get_id(cls, item: T_Resource) -> T_ID:
        raise NotImplementedError("Datapoints do not have an id")

    def create(self, items: pd.DataFrame | Sequence[pd.DataFrame]) -> pd.DataFrame | pd.DataFrame | None:
        for item in items:
            self.client.time_series.data.insert_dataframe(item)
        return None

    def load_file(self, filepath: Path, ToolGlobals: CDFToolConfig) -> T_Resource:
        if filepath.suffix == ".csv":
            return pd.read_csv(filepath, parse_dates=True, index_col=0)
        elif filepath.suffix == ".parquet":
            return pd.read_parquet(filepath, engine="pyarrow")
        else:
            raise ValueError(f"Not supported file type {filepath.suffix}")


class RawLoader(Loader[str, pd.DataFrame, list[pd.DataFrame]]):
    load_files_individually = True
    name = "raw"
    resource_cls = pd.DataFrame
    actions = frozenset({RawAcl.Action.Read, RawAcl.Action.Write})
    acl = RawAcl
    default_db: str = "default"

    def __init__(self, client: CogniteClient):
        super().__init__(client)
        self.db = self.default_db
        self.table = ""

    @classmethod
    def get_id(cls, item: T_Resource) -> T_ID:
        raise NotImplementedError("Raw data does not have an id")

    def load_file(self, filepath: Path, ToolGlobals: CDFToolConfig) -> pd.DataFrame:
        for pattern in [r"(\d+)\.(\w+)\.(\w+)", r"(\d+)\.(\w+)"]:
            if match := re.match(pattern, filepath.name):
                self.db = match.group(2)
                self.table = match.group(3)
                break
        else:
            print(f"[bold red]ERROR:[/] Filename {filepath.name} does not match expected format.")
            ToolGlobals.failed = True
            return pd.DataFrame()
        if filepath.suffix == ".csv":
            df = pd.read_csv(filepath, dtype=str)
            df.fillna("", inplace=True)
            return df
        elif filepath.suffix == ".parquet":
            return pd.read_parquet(filepath, engine="pyarrow")
        else:
            raise ValueError(f"Not supported file type {filepath.suffix}")

    def create(self, items: pd.DataFrame | Sequence[pd.DataFrame]) -> pd.DataFrame | list[pd.DataFrame] | None:
        for item in items:
            self.client.raw.rows.insert_dataframe(
                db_name=self.db,
                table_name=self.table,
                dataframe=item,
                ensure_parent=True,
            )
        # Set the default db back
        self.db = self.default_db
        self.table = ""
        return None


def load_resources(
    LoaderCls: type[Loader],
    path: Path,
    ToolGlobals: CDFToolConfig,
    drop: bool,
    dry_run: bool = False,
):
    loader = LoaderCls.create_loader(ToolGlobals)
    if path.is_file():
        if path.suffix not in loader.filetypes:
            raise ValueError("Invalid file type")
        files = [path]
    else:
        files = [file for type_ in loader.filetypes for file in path.glob(f"**/*.{type_}")]

    items: Iterable[Sequence[T_Resource]]
    if loader.load_files_individually:
        items = ([loader.load_file(f, ToolGlobals)] for f in files)
    else:
        items = [loader.list_cls([item for f in files for item in loader.load_file(f, ToolGlobals)])]

    for batch in items:
        if len(batch) == 0:
            return
        print(f"[bold]Uploading {len(batch)} {loader.name} to CDF...[/]")

        drop_items: list[T_ID] = []
        for item in batch:
            # Set the context info for this CDF project
            if hasattr(item, "data_set_id"):
                item.data_set_id = ToolGlobals.data_set_id
            if drop:
                drop_items.append(loader.get_id(item))
        try:
            if drop:
                if not dry_run:
                    loader.delete(drop_items)
                    print(f"  Deleted {len(drop_items)} {loader.name}.")
                else:
                    print(f"  Would have deleted {len(batch)} {loader.name}.")
        except CogniteAPIError:
            print(f"[bold red]ERROR:[/] Failed to delete {drop_items}. They may not exist.")
        try:
            if not dry_run:
                loader.create(batch)
            else:
                print(f"  Would have created {len(batch)} {loader.name}.")
        except Exception as e:
            print(f"[bold red]ERROR:[/] Failed to upload {loader.name}.")
            print(e)
            ToolGlobals.failed = True
            return
        print(f"  Created {len(batch)} timeseries from {len(files)} files.")


def load_raw(
    ToolGlobals: CDFToolConfig,
    file: str,
    raw_db: str = "default",
    drop: bool = False,
    dry_run: bool = False,
    directory=None,
) -> None:
    """Load raw data from csv files into CDF Raw

    Args:
        file: name of file to load, if empty load all files
        drop: whether to drop existing data
    """
    if directory is None:
        raise ValueError("directory must be specified")
    client: CogniteClient = ToolGlobals.verify_client(capabilities={"rawAcl": ["READ", "WRITE"]})

    files = []
    if file:
        # Only load the supplied filename.
        files.append(file)
    else:
        # Pick up all the .csv files in the data folder.
        for _, _, filenames in os.walk(directory):
            for f in filenames:
                if ".csv" in f:
                    files.append(f)
    files.sort()
    if len(files) == 0:
        return
    print(f"[bold]Uploading {len(files)} .csv files to RAW database using {raw_db} if not set in filename...[/]")
    for f in files:
        try:
            (_, db, table_name) = re.match(r"(\d+)\.(\w+)\.(\w+)\.csv", f).groups()
        except AttributeError:
            db = raw_db
            try:
                (_, table_name) = re.match(r"(\d+)\.(\w+)\.csv", f).groups()
            except AttributeError:
                print(f"[bold red]ERROR:[/] Filename {f} does not match expected format.")
                ToolGlobals.failed = True
                return
        with open(f"{directory}/{f}", mode="rb") as file:
            # The replacement is used to ensure that we read exactly the same file on Windows and Linux
            file_content = file.read().replace(b"\r\n", b"\n").decode("utf-8")
            dataframe = pd.read_csv(io.StringIO(file_content), dtype=str)
            dataframe = dataframe.fillna("")
            try:
                if not dry_run:
                    if drop:
                        try:
                            client.raw.tables.delete(db, table_name)
                        except Exception:
                            ...
                    try:
                        client.raw.databases.create(db)
                        print("  Created database: " + db)
                    except Exception:
                        ...
                    client.raw.rows.insert_dataframe(
                        db_name=db,
                        table_name=table_name,
                        dataframe=dataframe,
                        ensure_parent=True,
                    )
                    print("  Deleted table: " + table_name)
                    print(f"  Uploaded {f} to {db} RAW database.")
                else:
                    print("  Would have deleted table: " + table_name)
                    print(f"  Would have uploaded {f} to {db} RAW database.")
            except Exception as e:
                print(f"[bold red]ERROR:[/] Failed to upload {f}")
                print(e)
                ToolGlobals.failed = True
                return


def load_files(
    ToolGlobals: CDFToolConfig,
    id_prefix: str = "example",
    file: str | None = None,
    drop: bool = False,
    dry_run: bool = False,
    directory=None,
) -> None:
    if directory is None:
        raise ValueError("directory must be specified")
    try:
        client = ToolGlobals.verify_client(capabilities={"filesAcl": ["READ", "WRITE"]})
        files = []
        if file is not None and len(file) > 0:
            files.append(file)
        else:
            # Pick up all the files in the files folder.
            for _, _, filenames in os.walk(directory):
                for f in filenames:
                    files.append(f)
        if len(files) == 0:
            return
        print(f"[bold]Uploading {len(files)} files/documents to CDF...[/]")
        for f in files:
            if not dry_run:
                client.files.upload(
                    path=f"{directory}/{f}",
                    data_set_id=ToolGlobals.data_set_id,
                    name=f,
                    external_id=id_prefix + "_" + f,
                    overwrite=drop,
                )
        if not dry_run:
            print(f"  Uploaded successfully {len(files)} files/documents.")
        else:
            print(f"  Would have uploaded {len(files)} files/documents.")
    except Exception as e:
        print("[bold red]ERROR:[/] Failed to upload files")
        print(e)
        ToolGlobals.failed = True
        return


def load_timeseries_metadata(
    ToolGlobals: CDFToolConfig,
    file: str,
    drop: bool,
    dry_run: bool = False,
    directory=None,
) -> None:
    return load_resources(
        TimeSeriesLoader,
        (file and Path(file)) or Path(directory),
        ToolGlobals,
        drop,
        dry_run,
    )


def load_timeseries_datapoints(ToolGlobals: CDFToolConfig, file: str | None = None, dry_run: bool = False, directory=None) -> None:
    return load_resources(
        DatapointsLoader,
        (file and Path(file)) or Path(directory),
        ToolGlobals,
        False,
        dry_run,
    )


def load_transformations(
    ToolGlobals: CDFToolConfig,
    file: str | None = None,
    drop: bool = False,
    dry_run: bool = False,
    directory: str | None = None,
) -> None:
    """Load transformations from dump folder.

    This code only gives a partial support for transformations by loading the actual sql query and the
    necessary config. Schedules, authentication, etc is not supported.
    """
    return load_resources(
        TransformationLoader,
        (file and Path(file)) or Path(directory),
        ToolGlobals,
        drop,
        dry_run,
    )


def load_groups(
    ToolGlobals: CDFToolConfig,
    file: str | None = None,
    directory: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
    load_resources(
        GroupLoader,
        (file and Path(file)) or Path(directory),
        ToolGlobals,
        False,
        dry_run,
    )


def load_datamodel_graphql(
    ToolGlobals: CDFToolConfig,
    space_name: str | None = None,
    model_name: str | None = None,
    directory=None,
) -> None:
    """Load a graphql datamodel from file."""
    if space_name is None or model_name is None or directory is None:
        raise ValueError("space_name, model_name, and directory must be supplied.")
    with open(f"{directory}/datamodel.graphql") as file:
        # Read directly into a string.
        datamodel = file.read()
    # Clear any delete errors
    ToolGlobals.failed = False
    client = ToolGlobals.verify_client(
        capabilities={
            "dataModelsAcl": ["READ", "WRITE"],
            "dataModelInstancesAcl": ["READ", "WRITE"],
        }
    )
    print(f"[bold]Loading data model {model_name} into space {space_name} from {directory}...[/]")
    try:
        client.data_modeling.graphql.apply_dml(
            (space_name, model_name, "1"),
            dml=datamodel,
            name=model_name,
            description=f"Data model for {model_name}",
        )
    except Exception as e:
        print(f"[bold red]ERROR:[/] Failed to write data model {model_name} to space {space_name}.")
        print(e)
        ToolGlobals.failed = True
        return
    print(f"  Created data model {model_name}.")


def load_datamodel(
    ToolGlobals: CDFToolConfig,
    drop: bool = False,
    delete_removed: bool = True,
    delete_containers: bool = False,
    delete_spaces: bool = False,
    directory: Path | None = None,
    dry_run: bool = False,
    only_drop: bool = False,
) -> None:
    """Load containers, views, spaces, and data models from a directory

        Note that this function will never delete instances, but will delete all
        the properties found in containers if delete_containers is specified.
        delete_spaces will fail unless also the edges and nodes have been deleted,
        e.g. using the clean_out_datamodel() function.

        Note that if delete_spaces flag is True, an attempt will be made to delete the space,
        but if it fails, the loading will continue. If delete_containers is True, the loading
        will abort if deletion fails.
    Args:
        drop: Whether to drop all existing resources before loading.
        delete_removed: Whether to delete (previous) resources that are not in the directory.
        delete_containers: Whether to delete containers including data in the instances.
        delete_spaces: Whether to delete spaces (requires containers and instances to be deleted).
        directory: Directory to load from.
        dry_run: Whether to perform a dry run and only print out what will happen.
        only_drop: Whether to only drop existing resources and not load new ones.
    """
    if directory is None:
        raise ValueError("directory must be supplied.")
    model_files_by_type: dict[str, list[Path]] = defaultdict(list)
    models_pattern = re.compile(r"^.*\.?(space|container|view|datamodel)\.yaml$")
    for file in directory.rglob("*.yaml"):
        if not (match := models_pattern.match(file.name)):
            continue
        model_files_by_type[match.group(1)].append(file)
    print("[bold]Loading...[/]")
    for type_, files in model_files_by_type.items():
        model_files_by_type[type_].sort()
        print(f"  {len(files)} of type {type_}s in {directory}")

    cognite_resources_by_type: dict[str, list[ContainerApply | ViewApply | DataModelApply | SpaceApply]] = defaultdict(
        list
    )
    for type_, files in model_files_by_type.items():
        resource_cls = {
            "space": SpaceApply,
            "container": ContainerApply,
            "view": ViewApply,
            "datamodel": DataModelApply,
        }[type_]
        for file in files:
            cognite_resources_by_type[type_].append(
                resource_cls.load(load_yaml_inject_variables(file, ToolGlobals.environment_variables()))
            )
    # Remove duplicates
    for type_ in list(cognite_resources_by_type):
        unique = {r.as_id(): r for r in cognite_resources_by_type[type_]}
        cognite_resources_by_type[type_] = list(unique.values())

    explicit_space_list = [s.space for s in cognite_resources_by_type["space"]]
    space_list = list({r.space for _, resources in cognite_resources_by_type.items() for r in resources})

    implicit_spaces = [SpaceApply(space=s, name=s, description="Imported space") for s in space_list]
    for s in implicit_spaces:
        if s.name not in [s2.name for s2 in cognite_resources_by_type["space"]]:
            cognite_resources_by_type["space"].append(s)
    nr_of_spaces = len(cognite_resources_by_type["space"])
    print(f"  found {len(implicit_spaces)} space(s) referenced in config files giving a total of {nr_of_spaces}")
    # Clear any delete errors
    ToolGlobals.failed = False
    client = ToolGlobals.verify_client(
        capabilities={
            "dataModelsAcl": ["READ", "WRITE"],
            "dataModelInstancesAcl": ["READ", "WRITE"],
        }
    )

    existing_resources_by_type: dict[str, list[ContainerApply | ViewApply | DataModelApply | SpaceApply]] = defaultdict(
        list
    )
    resource_api_by_type = {
        "container": client.data_modeling.containers,
        "view": client.data_modeling.views,
        "datamodel": client.data_modeling.data_models,
        "space": client.data_modeling.spaces,
    }
    for type_, resources in cognite_resources_by_type.items():
        existing_resources_by_type[type_] = resource_api_by_type[type_].retrieve(list({r.as_id() for r in resources}))

    differences: dict[str, Difference] = {}
    for type_, resources in cognite_resources_by_type.items():
        new_by_id = {r.as_id(): r for r in resources}
        existing_by_id = {r.as_id(): r for r in existing_resources_by_type[type_]}

        added = [r for r in resources if r.as_id() not in existing_by_id]
        removed = [r for r in existing_resources_by_type[type_] if r.as_id() not in new_by_id]

        changed = []
        unchanged = []
        for existing_id in set(new_by_id.keys()) & set(existing_by_id.keys()):
            if new_by_id[existing_id] == existing_by_id[existing_id]:
                unchanged.append(new_by_id[existing_id])
            else:
                changed.append(new_by_id[existing_id])

        differences[type_] = Difference(added, removed, changed, unchanged)

    creation_order = ["space", "container", "view", "datamodel"]

    if drop:
        print("[bold]Deleting existing configurations...[/]")
        # Clean out all old resources
        for type_ in reversed(creation_order):
            items = differences.get(type_)
            if items is None:
                continue
            if type_ == "container" and not delete_containers:
                print("  [bold]INFO:[/] Skipping deletion of containers as delete_containers flag is not set...")
                continue
            if type_ == "space" and not delete_spaces:
                print("  [bold]INFO:[/] Skipping deletion of spaces as delete_spaces flag is not set...")
                continue
            deleted = 0
            for i in items:
                if len(i) == 0:
                    continue
                # for i2 in i:
                try:
                    if not dry_run:
                        if type_ == "space":
                            for i2 in i:
                                # Only delete spaces that have been explicitly defined
                                if i2.space in explicit_space_list:
                                    delete_instances(
                                        ToolGlobals,
                                        space_name=i2.space,
                                        dry_run=dry_run,
                                    )
                                    ret = resource_api_by_type["space"].delete(i2.space)
                                    if len(ret) > 0:
                                        deleted += 1
                        else:
                            ret = resource_api_by_type[type_].delete([i2.as_id() for i2 in i])
                            deleted += len(ret)
                except CogniteAPIError as e:
                    # Typically spaces can not be deleted if there are other
                    # resources in the space.
                    print(f"  [bold]ERROR:[/] Failed to delete {type_}(s):\n{e}")
                    if type_ == "space":
                        ToolGlobals.failed = False
                        print("  [bold]INFO:[/] Deletion of space was not successful, continuing.")
                        continue
                    return
            if not dry_run:
                print(f"  Deleted {deleted} {type_}(s).")
            else:
                print(f"  Would have deleted {deleted} {type_}(s).")

    if not only_drop:
        print("[bold]Creating new configurations...[/]")
        for type_ in creation_order:
            if type_ not in differences:
                continue
            items = differences[type_]
            if items.added:
                print(f"  {len(items.added)} added {type_}(s) to be created...")
                if dry_run:
                    continue
                attempts = 5
                while attempts > 0:
                    try:
                        resource_api_by_type[type_].apply(items.added)
                        attempts = 0
                    except Exception as e:
                        attempts -= 1
                        if attempts > 0:
                            continue
                        print(f"[bold]ERROR:[/] Failed to create {type_}(s):\n{e}")
                        ToolGlobals.failed = True
                        return
                print(f"  Created {len(items.added)} {type_}(s).")
            elif items.changed:
                print(f"  {len(items.added)} changed {type_}(s) to be created...")
                if dry_run:
                    continue
                attempts = 5
                while attempts > 0:
                    try:
                        resource_api_by_type[type_].apply(items.changed)
                        attempts = 0
                    except Exception as e:
                        attempts -= 1
                        if attempts > 0:
                            continue
                        print(f"[bold]ERROR:[/] Failed to create {type_}(s):\n{e}")
                        ToolGlobals.failed = True
                        return
                if drop:
                    print(
                        f"  Created {len(items.changed)} {type_}s that could have been updated instead (--drop specified)."
                    )
                else:
                    print(f"  Updated {len(items.changed)} {type_}(s).")
            elif items.unchanged:
                print(f"  {len(items.unchanged)} unchanged {type_}(s).")
                if drop:
                    attempts = 5
                    while attempts > 0:
                        try:
                            resource_api_by_type[type_].apply(items.unchanged)
                            attempts = 0
                        except Exception as e:
                            attempts -= 1
                            if attempts > 0:
                                continue
                            print(f"[bold]ERROR:[/] Failed to create {type_}(s):\n{e}")
                            ToolGlobals.failed = True
                            return
                    print(
                        f"  Created {len(items.changed)} unchanged {type_}(s) that could have been skipped (--drop specified)."
                    )

    if delete_removed and not drop:
        for type_ in reversed(creation_order):
            if type_ not in differences:
                continue
            items = differences[type_]
            if items.removed:
                if dry_run:
                    print(f"  Would have deleted {len(items.removed)} {type_}(s).")
                    continue
                try:
                    resource_api_by_type[type_].delete(items.removed)
                except CogniteAPIError as e:
                    # Typically spaces can not be deleted if there are other
                    # resources in the space.
                    print(f"[bold]ERROR:[/] Failed to delete {len(items.removed)} {type_}(s).")
                    print(e)
                    ToolGlobals.failed = True
                    continue
                print(f"  Deleted {len(items.removed)} {type_}(s) that were removed.")


def load_nodes(
    ToolGlobals: CDFToolConfig,
    directory: Path | None = None,
    dry_run: bool = False,
) -> None:
    """Insert nodes"""

    for file in directory.rglob("*.node.yaml"):
        if file.name == "config.yaml":
            continue

        client: CogniteClient = ToolGlobals.verify_client(
            capabilities={
                "dataModelsAcl": ["READ"],
                "dataModelInstancesAcl": ["READ", "WRITE"],
            }
        )

        nodes: dict = load_yaml_inject_variables(file, ToolGlobals.environment_variables())

        try:
            view = ViewId(
                space=nodes["view"]["space"],
                external_id=nodes["view"]["externalId"],
                version=nodes["view"]["version"],
            )
        except KeyError:
            raise KeyError(
                f"Expected view configuration not found in {file}:\nview:\n  space: <space>\n  externalId: <view_external_id>\n  version: <view_version>"
            )

        try:
            node_space: str = nodes["destination"]["space"]
        except KeyError:
            raise KeyError(
                f"Expected destination space configuration in {file}:\ndestination:\n  space: <destination_space_external_id>"
            )
        node_list: NodeApplyList = []
        try:
            for n in nodes.get("nodes", []):
                node_list.append(
                    NodeApply(
                        space=node_space,
                        external_id=n.pop("externalId"),
                        existing_version=n.pop("existingVersion", None),
                        sources=[NodeOrEdgeData(source=view, properties=n)],
                    )
                )
        except Exception as e:
            raise KeyError(f"Failed to parse node {n} in {file}:\n{e}")
        print(f"[bold]Loading {len(node_list)} nodes from {directory}...[/]")
        if not dry_run:
            try:
                client.data_modeling.instances.apply(
                    nodes=node_list,
                    auto_create_direct_relations=nodes.get("autoCreateDirectRelations", True),
                    skip_on_version_conflict=nodes.get("skipOnVersionConflict", False),
                    replace=nodes.get("replace", False),
                )
                print(f"  Created {len(node_list)} nodes in {node_space}.")
            except CogniteAPIError as e:
                print(f"[bold]ERROR:[/] Failed to create {len(node_list)} node(s) in {node_space}:\n{e}")
                ToolGlobals.failed = True
                return
