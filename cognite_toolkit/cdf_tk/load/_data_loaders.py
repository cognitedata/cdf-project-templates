from __future__ import annotations

import io
import re
from pathlib import Path
from typing import final

import pandas as pd
import yaml
from cognite.client.data_classes import capabilities
from cognite.client.data_classes.capabilities import Capability, FilesAcl, RawAcl, TimeSeriesAcl

from cognite_toolkit.cdf_tk.utils import CDFToolConfig

from ._base_loaders import DataLoader
from ._resource_loaders import FileMetadataLoader, RawDatabaseLoader, RawTableLoader, TimeSeriesLoader
from .data_classes import RawDatabaseTable


@final
class DatapointsLoader(DataLoader):
    item_name = "datapoints"
    folder_name = "timeseries_datapoints"
    filetypes = frozenset({"csv", "parquet"})
    dependencies = frozenset({TimeSeriesLoader})

    @classmethod
    def get_required_capability(cls, ToolGlobals: CDFToolConfig) -> Capability:
        scope: capabilities.AllScope | capabilities.DataSetScope = (
            TimeSeriesAcl.Scope.DataSet([ToolGlobals.data_set_id])
            if ToolGlobals.data_set_id
            else TimeSeriesAcl.Scope.All()
        )

        return TimeSeriesAcl(
            [TimeSeriesAcl.Action.Read, TimeSeriesAcl.Action.Write],
            scope,
        )

    def upload(self, datafile: Path, dry_run: bool) -> tuple[str, int]:
        if datafile.suffix == ".csv":
            # The replacement is used to ensure that we read exactly the same file on Windows and Linux
            file_content = datafile.read_bytes().replace(b"\r\n", b"\n").decode("utf-8")
            data = pd.read_csv(io.StringIO(file_content), parse_dates=True, index_col=0)
            data.index = pd.DatetimeIndex(data.index)
        elif datafile.suffix == ".parquet":
            data = pd.read_parquet(datafile, engine="pyarrow")
        else:
            raise ValueError(f"Unsupported file type {datafile.suffix} for {datafile.name}")
        if dry_run:
            return f"Would insert '{len(data):,}x{len(data.columns):,}' datapoints from '{datafile!s}'", len(
                data
            ) * len(data.columns)
        else:
            self.client.time_series.data.insert_dataframe(data)
            return f"Inserted '{len(data):,}x{len(data.columns):,}' datapoints from '{datafile!s}'", len(data) * len(
                data.columns
            )


@final
class FileLoader(DataLoader):
    item_name = "file contents"
    folder_name = "files"
    filetypes = frozenset()
    exclude_filetypes = frozenset({"yml", "yaml"})
    dependencies = frozenset({FileMetadataLoader})

    @property
    def display_name(self) -> str:
        return "file contents"

    @classmethod
    def get_required_capability(cls, ToolGlobals: CDFToolConfig) -> Capability | list[Capability]:
        scope: capabilities.AllScope | capabilities.DataSetScope
        if ToolGlobals.data_set_id is None:
            scope = FilesAcl.Scope.All()
        else:
            scope = FilesAcl.Scope.DataSet([ToolGlobals.data_set_id])

        return FilesAcl([FilesAcl.Action.Read, FilesAcl.Action.Write], scope)

    def upload(self, datafile: Path, dry_run: bool) -> tuple[str, int]:
        if dry_run:
            return f"Would upload file '{datafile!s}'", 1
        else:
            self.client.files.upload(path=str(datafile), name=datafile.name, overwrite=False)
            return f"Uploaded file '{datafile!s}'", 1


@final
class RawFileLoader(DataLoader):
    item_name = "rows"
    folder_name = "raw"
    filetypes = frozenset({"csv", "parquet"})
    dependencies = frozenset({RawDatabaseLoader, RawTableLoader})

    @classmethod
    def get_required_capability(cls, ToolGlobals: CDFToolConfig) -> Capability:
        return RawAcl([RawAcl.Action.Read, RawAcl.Action.Write], RawAcl.Scope.All())

    def upload(self, datafile: Path, dry_run: bool) -> tuple[str, int]:
        pattern = re.compile(rf"^(\d+\.)?{datafile.stem}\.(yml|yaml)$")
        metadata_file = next((filepath for filepath in datafile.parent.glob("*") if pattern.match(filepath.name)), None)
        if metadata_file is not None:
            raw = yaml.safe_load(metadata_file.read_text())
            if isinstance(raw, dict):
                metadata = RawDatabaseTable.load(raw)
            elif isinstance(raw, list):
                raise ValueError(f"Array/list format currently not supported for uploading {self.display_name}.")
            else:
                raise ValueError(f"Invalid format on metadata for {datafile.name}")
        else:
            raise ValueError(f"Missing metadata file for {datafile.name}. It should be named {datafile.stem}.yaml")

        if datafile.suffix == ".csv":
            # The replacement is used to ensure that we read exactly the same file on Windows and Linux
            file_content = datafile.read_bytes().replace(b"\r\n", b"\n").decode("utf-8")
            data = pd.read_csv(io.StringIO(file_content), dtype=str)
            data.fillna("", inplace=True)
        elif datafile.suffix == ".parquet":
            data = pd.read_parquet(datafile, engine="pyarrow")
        else:
            raise ValueError(f"Unsupported file type {datafile.suffix} for {datafile.name}")

        if dry_run:
            return f"Would insert '{len(data):,}x{len(data.columns):,}' rows from '{datafile!s}'", len(data)

        if metadata.table_name is None:
            raise ValueError(f"Missing table name for {datafile.name}")
        self.client.raw.rows.insert_dataframe(
            db_name=metadata.db_name, table_name=metadata.table_name, dataframe=data, ensure_parent=False
        )
        return f"Inserted '{len(data):,}x{len(data.columns):,}' rows from '{datafile!s}'", len(data)
