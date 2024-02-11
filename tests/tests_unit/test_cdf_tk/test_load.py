from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from cognite.client import data_modeling as dm
from cognite.client.data_classes import DataSet
from pytest import MonkeyPatch

from cognite_toolkit.cdf_tk.load import (
    AuthLoader,
    DatapointsLoader,
    DataSetsLoader,
    FileMetadataLoader,
    ResourceLoader,
    TimeSeriesLoader,
    ViewLoader,
)
from cognite_toolkit.cdf_tk.templates import (
    COGNITE_MODULES,
    build_config,
)
from cognite_toolkit.cdf_tk.templates.data_classes import (
    BuildConfigYAML,
    SystemYAML,
)
from cognite_toolkit.cdf_tk.utils import CDFToolConfig
from tests.tests_unit.approval_client import ApprovalCogniteClient
from tests.tests_unit.test_cdf_tk.constants import BUILD_DIR, PYTEST_PROJECT
from tests.tests_unit.utils import mock_read_yaml_file

THIS_FOLDER = Path(__file__).resolve().parent

DATA_FOLDER = THIS_FOLDER / "load_data"
SNAPSHOTS_DIR = THIS_FOLDER / "load_data_snapshots"


@pytest.mark.parametrize(
    "loader_cls, directory",
    [
        (FileMetadataLoader, DATA_FOLDER / "files"),
        (DatapointsLoader, DATA_FOLDER / "timeseries_datapoints"),
    ],
)
def test_loader_class(
    loader_cls: type[ResourceLoader], directory: Path, cognite_client_approval: ApprovalCogniteClient, data_regression
):
    cdf_tool = MagicMock(spec=CDFToolConfig)
    cdf_tool.verify_client.return_value = cognite_client_approval.mock_client
    cdf_tool.verify_capabilities.return_value = cognite_client_approval.mock_client
    cdf_tool.data_set_id = 999

    loader_cls.create_loader(cdf_tool).deploy_resources(directory, cdf_tool, dry_run=False)

    dump = cognite_client_approval.dump()
    data_regression.check(dump, fullpath=SNAPSHOTS_DIR / f"{directory.name}.yaml")


class DataSetsLoaderTest:
    def test_upsert_data_set(self, cognite_client_approval: ApprovalCogniteClient):
        cdf_tool = MagicMock(spec=CDFToolConfig)
        cdf_tool.verify_client.return_value = cognite_client_approval.mock_client
        cdf_tool.verify_capabilities.return_value = cognite_client_approval.mock_client

        loader = DataSetsLoader.create_loader(cdf_tool)
        loaded = loader.load_resource(DATA_FOLDER / "data_sets" / "1.my_datasets.yaml", cdf_tool, skip_validation=False)
        assert len(loaded) == 2

        first = DataSet.load(loaded[0].dump())
        # Set the properties that are set on the server side
        first.id = 42
        first.created_time = 42
        first.last_updated_time = 42
        # Simulate that the data set is already in CDF
        cognite_client_approval.append(DataSet, first)

        to_create, to_change, unchanged = loader.to_create_changed_unchanged_triple(loaded)

        assert len(to_create) == 1
        assert len(to_change) == 0
        assert len(unchanged) == 1


class TestViewLoader:
    def test_update_view_with_interface(self, cognite_client_approval: ApprovalCogniteClient):
        cdf_tool = MagicMock(spec=CDFToolConfig)
        cdf_tool.verify_client.return_value = cognite_client_approval.mock_client
        cdf_tool.verify_capabilities.return_value = cognite_client_approval.mock_client
        prop1 = dm.MappedProperty(
            dm.ContainerId(space="sp_space", external_id="container_id"),
            "prop1",
            type=dm.Text(),
            nullable=True,
            auto_increment=False,
        )
        interface = dm.View(
            space="sp_space",
            external_id="interface",
            version="1",
            properties={"prop1": prop1},
            last_updated_time=1,
            created_time=1,
            description=None,
            name=None,
            filter=None,
            implements=None,
            writable=True,
            used_for="node",
            is_global=False,
        )
        # Note that child views always contain all properties of their parent interfaces.
        child_cdf = dm.View(
            space="sp_space",
            external_id="child",
            version="1",
            properties={"prop1": prop1},
            last_updated_time=1,
            created_time=1,
            description=None,
            name=None,
            filter=None,
            implements=[interface.as_id()],
            writable=True,
            used_for="node",
            is_global=False,
        )
        child_local = dm.ViewApply(
            space="sp_space",
            external_id="child",
            version="1",
            implements=[interface.as_id()],
        )
        # Simulating that the interface and child_cdf are available in CDF
        cognite_client_approval.append(dm.View, [interface, child_cdf])

        loader = ViewLoader.create_loader(cdf_tool)
        to_create, to_change, unchanged = loader.to_create_changed_unchanged_triple(dm.ViewApplyList([child_local]))

        assert len(to_create) == 0
        assert len(to_change) == 0
        assert len(unchanged) == 1


class TestAuthLoader:

    scoped_content = """
name: 'scoped_group_name'
sourceId: '123'
capabilities:
    - datasetsAcl:
        actions:
            - READ
            - OWNER
        scope:
            idScope: { ids: ["site:001:b60:ds"] }

    - assetsAcl:
        actions:
            - READ
            - WRITE
        scope:
            datasetScope: {
                ids: ['ds_asset_oid']
            }
    - extractionConfigsAcl:
        actions:
            - READ
        scope:
            extractionPipelineScope: {
                ids: ['ep_src_asset_oid']
            }

    - sessionsAcl:
        actions:
            - LIST
            - CREATE
            - DELETE
        scope:
            all: {}
    """

    unscoped_content = """
    name: 'unscoped_group_name'
    sourceId: '123'
    capabilities:

        - assetsAcl:
            actions:
                - READ
                - WRITE
            scope:
                all: {}
        - sessionsAcl:
            actions:
                - LIST
                - CREATE
                - DELETE
            scope:
                all: {}

"""

    def test_load_all(self, cdf_tool_config: CDFToolConfig, monkeypatch: MonkeyPatch):

        loader = AuthLoader.create_loader(cdf_tool_config, "all")

        mock_read_yaml_file({"group_file.yaml": yaml.safe_load(self.unscoped_content)}, monkeypatch)
        loaded = loader.load_resource(Path("group_file.yaml"), cdf_tool_config, skip_validation=True)
        assert loaded.name == "unscoped_group_name"

        mock_read_yaml_file({"group_file.yaml": yaml.safe_load(self.scoped_content)}, monkeypatch)
        loaded = loader.load_resource(Path("group_file.yaml"), cdf_tool_config, skip_validation=True)
        assert loaded.name == "scoped_group_name"

        caps = {str(type(element).__name__): element for element in loaded.capabilities}

        assert all(isinstance(item, int) for item in caps["DataSetsAcl"].scope.ids)
        assert all(isinstance(item, int) for item in caps["AssetsAcl"].scope.ids)
        assert all(isinstance(item, int) for item in caps["ExtractionConfigsAcl"].scope.ids)
        assert caps["SessionsAcl"].scope._scope_name == "all"

    def test_load_all_scoped_only(self, cdf_tool_config: CDFToolConfig, monkeypatch: MonkeyPatch):

        loader = AuthLoader.create_loader(cdf_tool_config, "all_scoped_only")

        mock_read_yaml_file({"group_file.yaml": yaml.safe_load(self.unscoped_content)}, monkeypatch)
        loaded = loader.load_resource(Path("group_file.yaml"), cdf_tool_config, skip_validation=True)
        assert loaded.name == "unscoped_group_name"

        mock_read_yaml_file({"group_file.yaml": yaml.safe_load(self.scoped_content)}, monkeypatch)
        loaded = loader.load_resource(Path("group_file.yaml"), cdf_tool_config, skip_validation=True)
        assert loaded is None

    def test_load_resource_scoped_only(self, cdf_tool_config: CDFToolConfig, monkeypatch: MonkeyPatch):

        loader = AuthLoader.create_loader(cdf_tool_config, "resource_scoped_only")

        mock_read_yaml_file({"group_file.yaml": yaml.safe_load(self.unscoped_content)}, monkeypatch)
        loaded = loader.load_resource(Path("group_file.yaml"), cdf_tool_config, skip_validation=True)
        assert loaded is None

        mock_read_yaml_file({"group_file.yaml": yaml.safe_load(self.scoped_content)}, monkeypatch)
        loaded = loader.load_resource(Path("group_file.yaml"), cdf_tool_config, skip_validation=True)
        assert loaded.name == "scoped_group_name"
        assert len(loaded.capabilities) == 4

        caps = {str(type(element).__name__): element for element in loaded.capabilities}

        assert all(isinstance(item, int) for item in caps["DataSetsAcl"].scope.ids)
        assert all(isinstance(item, int) for item in caps["AssetsAcl"].scope.ids)
        assert all(isinstance(item, int) for item in caps["ExtractionConfigsAcl"].scope.ids)
        assert caps["SessionsAcl"].scope._scope_name == "all"


class TestTimeSeriesLoader:
    timeseries_yaml = """
externalId: pi_160696
name: VAL_23-PT-92504:X.Value
dataSetExternalId: ds_timeseries_oid
isString: false
metadata:
  compdev: '0'
  location5: '2'
isStep: false
description: PH 1stStgSuctCool Gas Out
"""

    def test_load_skip_validation_no_preexisting_dataset(
        self,
        cognite_client_approval: ApprovalCogniteClient,
        cdf_tool_config_real: CDFToolConfig,
        monkeypatch: MonkeyPatch,
    ) -> None:
        loader = TimeSeriesLoader(cognite_client_approval.mock_client)
        mock_read_yaml_file({"timeseries.yaml": yaml.safe_load(self.timeseries_yaml)}, monkeypatch)
        loaded = loader.load_resource(Path("timeseries.yaml"), cdf_tool_config_real, skip_validation=True)

        assert len(loaded) == 1
        assert loaded[0].data_set_id == -1

    def test_load_skip_validation_with_preexisting_dataset(
        self,
        cognite_client_approval: ApprovalCogniteClient,
        cdf_tool_config_real: CDFToolConfig,
        monkeypatch: MonkeyPatch,
    ) -> None:
        cognite_client_approval.append(DataSet, DataSet(id=12345, external_id="ds_timeseries_oid"))
        loader = TimeSeriesLoader(cognite_client_approval.mock_client)

        mock_read_yaml_file({"timeseries.yaml": yaml.safe_load(self.timeseries_yaml)}, monkeypatch)

        loaded = loader.load_resource(Path("timeseries.yaml"), cdf_tool_config_real, skip_validation=True)

        assert len(loaded) == 1
        assert loaded[0].data_set_id == 12345


class TestDeployResources:
    def test_deploy_resource_order(self, cognite_client_approval: ApprovalCogniteClient):
        build_env = "dev"
        system_config = SystemYAML.load_from_directory(PYTEST_PROJECT / COGNITE_MODULES, build_env)
        config = BuildConfigYAML.load_from_directory(PYTEST_PROJECT, build_env)
        config.environment.selected_modules_and_packages = ["another_module"]
        build_config(BUILD_DIR, PYTEST_PROJECT, config=config, system_config=system_config, clean=True, verbose=False)
        expected_order = ["MyView", "MyOtherView"]
        cdf_tool = MagicMock(spec=CDFToolConfig)
        cdf_tool.verify_client.return_value = cognite_client_approval.mock_client
        cdf_tool.verify_capabilities.return_value = cognite_client_approval.mock_client

        ViewLoader.create_loader(cdf_tool).deploy_resources(BUILD_DIR, cdf_tool, dry_run=False)

        views = cognite_client_approval.dump(sort=False)["View"]

        actual_order = [view["externalId"] for view in views]

        assert actual_order == expected_order
