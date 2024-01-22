import pandas as pd
import pytest
from cognite.client import CogniteClient
from cognite.client import data_modeling as dm
from cognite.client.data_classes import TimeSeriesWrite, TimeSeriesWriteList

from cognite_toolkit.cdf_tk.load import ContainerLoader, TimeSeriesLoader
from tests.test_integration.constants import RUN_UNIQUE_ID


@pytest.fixture(scope="session")
def integration_space(cognite_client: CogniteClient) -> dm.Space:
    space = dm.SpaceApply(
        space="integration_test_cdf_tk",
        name="CDF Toolkit Test Space",
        description="Space used for running integration test",
    )
    return cognite_client.data_modeling.spaces.apply(space)


class TestTimeSeriesLoader:
    def test_create_populate_count_drop_data(self, cognite_client: CogniteClient) -> None:
        timeseries = TimeSeriesWrite(
            external_id=f"test_create_populate_count_drop_data{RUN_UNIQUE_ID}", is_string=False
        )
        datapoints = pd.DataFrame(
            [{"timestamp": 0, timeseries.external_id: 0}, {"timestamp": 1, timeseries.external_id: 1}]
        ).set_index("timestamp")
        datapoints.index = pd.to_datetime(datapoints.index, unit="s")
        loader = TimeSeriesLoader(client=cognite_client)
        ts_ids = [timeseries.external_id]

        try:
            created = loader.create(TimeSeriesWriteList([timeseries]))
            assert len(created) == 1

            assert loader.count(ts_ids) == 0
            cognite_client.time_series.data.insert_dataframe(datapoints)

            assert loader.count(ts_ids) == 2

            loader.drop_data(ts_ids)

            assert loader.count(ts_ids) == 0

            assert loader.delete(ts_ids) == 1

            assert not loader.retrieve(ts_ids)
        finally:
            cognite_client.time_series.delete(external_id=timeseries.external_id, ignore_unknown_ids=True)


@pytest.fixture(scope="function")
def node_container(cognite_client: CogniteClient, integration_space: dm.Space) -> dm.Container:
    container = dm.ContainerApply(
        space=integration_space.space,
        external_id=f"test_create_populate_count_drop_data{RUN_UNIQUE_ID}",
        name="Test Container",
        description="Container used for running integration test",
        used_for="node",
        properties={"name": dm.ContainerProperty(dm.Text())},
    )
    return cognite_client.data_modeling.containers.apply(container)


@pytest.fixture(scope="function")
def edge_container(cognite_client: CogniteClient, integration_space: dm.Space) -> dm.Container:
    container = dm.ContainerApply(
        space=integration_space.space,
        external_id=f"test_create_populate_count_drop_data_edge{RUN_UNIQUE_ID}",
        name="Test Container Edge",
        description="Container used for running integration test",
        used_for="edge",
        properties={"name": dm.ContainerProperty(dm.Text())},
    )
    return cognite_client.data_modeling.containers.apply(container)


class TestContainerLoader:
    def test_populate_count_drop_data_node_container(
        self, node_container: dm.Container, cognite_client: CogniteClient
    ) -> None:
        node = dm.NodeApply(
            space=node_container.space,
            external_id=f"test_create_populate_count_drop_data{RUN_UNIQUE_ID}",
            sources=[dm.NodeOrEdgeData(source=node_container.as_id(), properties={"name": "Anders"})],
        )
        container_id = [node_container.as_id()]

        loader = ContainerLoader(client=cognite_client)

        try:
            assert loader.count(container_id) == 0

            cognite_client.data_modeling.instances.apply(nodes=[node])

            assert loader.count(container_id) == 1

            loader.drop_data(container_id)
            assert loader.count(container_id) == 0

            write_container = node_container.as_write()
            write_container.description = "Updated description"
            updated = loader.update(dm.ContainerApplyList([write_container]))
            assert len(updated) == 1
            assert updated[0].description == write_container.description
        finally:
            loader.drop_data(container_id)

    def test_populate_count_drop_data_edge_container(
        self, edge_container: dm.Container, cognite_client: CogniteClient
    ) -> None:
        space = edge_container.space
        nodes = dm.NodeApplyList(
            [
                dm.NodeApply(
                    space=space,
                    external_id=f"test_create_populate_count_drop_data:start{RUN_UNIQUE_ID}",
                    sources=None,
                ),
                dm.NodeApply(
                    space=space,
                    external_id=f"test_create_populate_count_drop_data:end{RUN_UNIQUE_ID}",
                    sources=None,
                ),
            ]
        )
        edge = dm.EdgeApply(
            space=space,
            external_id=f"test_populate_count_drop_data_edge_container{RUN_UNIQUE_ID}",
            type=dm.DirectRelationReference(space, "test_edge_type"),
            start_node=(nodes[0].space, nodes[0].external_id),
            end_node=(nodes[1].space, nodes[1].external_id),
            sources=[dm.NodeOrEdgeData(source=edge_container.as_id(), properties={"name": "Anders"})],
        )
        container_id = [edge_container.as_id()]

        loader = ContainerLoader(client=cognite_client)

        try:
            assert loader.count(container_id) == 0

            cognite_client.data_modeling.instances.apply(edges=[edge], nodes=nodes)

            assert loader.count(container_id) == 1

            loader.drop_data(container_id)
            assert loader.count(container_id) == 0

            write_container = edge_container.as_write()
            write_container.description = "Updated description"
            updated = loader.update(dm.ContainerApplyList([write_container]))
            assert len(updated) == 1
            assert updated[0].description == write_container.description
        finally:
            cognite_client.data_modeling.instances.delete(nodes=nodes.as_ids(), edges=edge.as_id())
