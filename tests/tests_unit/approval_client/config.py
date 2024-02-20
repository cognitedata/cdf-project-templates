from __future__ import annotations

from cognite.client.data_classes import (
    Database,
    DatabaseList,
    DatabaseWrite,
    DatabaseWriteList,
    Datapoints,
    DatapointsList,
    DataSet,
    DataSetList,
    DataSetWrite,
    DataSetWriteList,
    ExtractionPipeline,
    ExtractionPipelineConfig,
    ExtractionPipelineConfigWrite,
    ExtractionPipelineConfigWriteList,
    ExtractionPipelineList,
    ExtractionPipelineWrite,
    ExtractionPipelineWriteList,
    FileMetadata,
    FileMetadataList,
    FileMetadataWrite,
    FileMetadataWriteList,
    Function,
    FunctionList,
    FunctionWrite,
    FunctionWriteList,
    Group,
    GroupList,
    GroupWrite,
    GroupWriteList,
    Row,
    RowList,
    RowWrite,
    RowWriteList,
    Table,
    TableList,
    TableWrite,
    TableWriteList,
    TimeSeries,
    TimeSeriesList,
    TimeSeriesWrite,
    TimeSeriesWriteList,
    Transformation,
    TransformationList,
    TransformationSchedule,
    TransformationScheduleList,
    TransformationScheduleWrite,
    TransformationScheduleWriteList,
    TransformationWrite,
    TransformationWriteList,
)
from cognite.client.data_classes.data_modeling import (
    Container,
    ContainerApply,
    ContainerApplyList,
    ContainerList,
    DataModel,
    DataModelApply,
    DataModelApplyList,
    DataModelList,
    Node,
    NodeApply,
    NodeApplyList,
    NodeList,
    Space,
    SpaceApply,
    SpaceApplyList,
    SpaceList,
    View,
    ViewApply,
    ViewApplyList,
    ViewList,
)
from cognite.client.data_classes.extractionpipelines import ExtractionPipelineConfigList
from cognite.client.data_classes.iam import TokenInspection

from .data_classes import APIResource, Method

# This is used to define the resources that should be mocked in the ApprovalCogniteClient
# You can add more resources here if you need to mock more resources
API_RESOURCES = [
    APIResource(
        api_name="post",
        resource_cls=TokenInspection,
        list_cls=list[TokenInspection],
        methods={
            "post": [Method(api_class_method="post", mock_name="post_method")],
        },
    ),
    APIResource(
        api_name="iam.groups",
        resource_cls=Group,
        _write_cls=GroupWrite,
        _write_list_cls=GroupWriteList,
        list_cls=GroupList,
        methods={
            "create": [Method(api_class_method="create", mock_name="create")],
            "delete": [Method(api_class_method="delete", mock_name="delete_id_external_id")],
            "retrieve": [Method(api_class_method="list", mock_name="return_values")],
        },
    ),
    APIResource(
        api_name="iam.token",
        resource_cls=TokenInspection,
        list_cls=list[TokenInspection],
        methods={
            "inspect": [Method(api_class_method="inspect", mock_name="return_value")],
        },
    ),
    APIResource(
        api_name="data_sets",
        resource_cls=DataSet,
        _write_cls=DataSetWrite,
        _write_list_cls=DataSetWriteList,
        list_cls=DataSetList,
        methods={
            "create": [Method(api_class_method="create", mock_name="create")],
            "retrieve": [
                Method(api_class_method="list", mock_name="return_values"),
                Method(api_class_method="retrieve", mock_name="return_value"),
                Method(api_class_method="retrieve_multiple", mock_name="return_values"),
            ],
        },
    ),
    APIResource(
        api_name="time_series",
        resource_cls=TimeSeries,
        _write_cls=TimeSeriesWrite,
        list_cls=TimeSeriesList,
        _write_list_cls=TimeSeriesWriteList,
        methods={
            "create": [Method(api_class_method="create", mock_name="create")],
            "delete": [Method(api_class_method="delete", mock_name="delete_id_external_id")],
            "retrieve": [
                Method(api_class_method="list", mock_name="return_values"),
                Method(api_class_method="retrieve", mock_name="return_values"),
                Method(api_class_method="retrieve_multiple", mock_name="return_values"),
            ],
        },
    ),
    APIResource(
        api_name="raw.databases",
        resource_cls=Database,
        _write_cls=DatabaseWrite,
        list_cls=DatabaseList,
        _write_list_cls=DatabaseWriteList,
        methods={
            "create": [Method(api_class_method="create", mock_name="create")],
            "retrieve": [Method(api_class_method="list", mock_name="return_values")],
            "delete": [Method(api_class_method="delete", mock_name="delete_raw")],
        },
    ),
    APIResource(
        api_name="raw.tables",
        resource_cls=Table,
        _write_cls=TableWrite,
        list_cls=TableList,
        _write_list_cls=TableWriteList,
        methods={
            "create": [Method(api_class_method="create", mock_name="create")],
            "retrieve": [Method(api_class_method="list", mock_name="return_values")],
            "delete": [Method(api_class_method="delete", mock_name="delete_raw")],
        },
    ),
    APIResource(
        api_name="raw.rows",
        resource_cls=Row,
        _write_cls=RowWrite,
        list_cls=RowList,
        _write_list_cls=RowWriteList,
        methods={
            "create": [Method(api_class_method="insert_dataframe", mock_name="insert_dataframe")],
            "delete": [Method(api_class_method="delete", mock_name="delete_raw")],
            "retrieve": [
                Method(api_class_method="list", mock_name="return_values"),
                Method(api_class_method="retrieve", mock_name="return_values"),
            ],
        },
    ),
    APIResource(
        api_name="functions",
        resource_cls=Function,
        _write_cls=FunctionWrite,
        list_cls=FunctionList,
        _write_list_cls=FunctionWriteList,
        methods={
            "create": [Method(api_class_method="create", mock_name="create_function_api")],
            "delete": [Method(api_class_method="delete", mock_name="delete_id_external_id")],
            "retrieve": [
                Method(api_class_method="list", mock_name="return_values"),
                Method(api_class_method="retrieve", mock_name="return_value"),
                Method(api_class_method="retrieve_multiple", mock_name="return_values"),
            ],
        },
    ),
    APIResource(
        api_name="functions.schedules",
        resource_cls=Function,
        _write_cls=FunctionWrite,
        list_cls=FunctionList,
        _write_list_cls=FunctionWriteList,
        methods={
            "create": [Method(api_class_method="create", mock_name="create_function_api")],
            "delete": [Method(api_class_method="delete", mock_name="delete_id_external_id")],
            "retrieve": [
                Method(api_class_method="list", mock_name="return_values"),
            ],
        },
    ),
    APIResource(
        api_name="transformations",
        resource_cls=Transformation,
        _write_cls=TransformationWrite,
        list_cls=TransformationList,
        _write_list_cls=TransformationWriteList,
        methods={
            "create": [Method(api_class_method="create", mock_name="create")],
            "delete": [Method(api_class_method="delete", mock_name="delete_id_external_id")],
            "retrieve": [
                Method(api_class_method="list", mock_name="return_values"),
                Method(api_class_method="retrieve", mock_name="return_value"),
                Method(api_class_method="retrieve_multiple", mock_name="return_values"),
            ],
        },
    ),
    APIResource(
        api_name="transformations.schedules",
        resource_cls=TransformationSchedule,
        _write_cls=TransformationScheduleWrite,
        list_cls=TransformationScheduleList,
        _write_list_cls=TransformationScheduleWriteList,
        methods={
            "create": [Method(api_class_method="create", mock_name="create")],
            "delete": [Method(api_class_method="delete", mock_name="delete_id_external_id")],
            "retrieve": [
                Method(api_class_method="list", mock_name="return_values"),
                Method(api_class_method="retrieve", mock_name="return_value"),
            ],
        },
    ),
    APIResource(
        api_name="extraction_pipelines",
        resource_cls=ExtractionPipeline,
        _write_cls=ExtractionPipelineWrite,
        list_cls=ExtractionPipelineList,
        _write_list_cls=ExtractionPipelineWriteList,
        methods={
            "create": [Method(api_class_method="create", mock_name="create")],
            "delete": [Method(api_class_method="delete", mock_name="delete_id_external_id")],
            "retrieve": [
                Method(api_class_method="list", mock_name="return_values"),
                Method(api_class_method="retrieve", mock_name="return_value"),
                Method(api_class_method="retrieve_multiple", mock_name="return_values"),
            ],
        },
    ),
    APIResource(
        api_name="extraction_pipelines.config",
        resource_cls=ExtractionPipelineConfig,
        _write_cls=ExtractionPipelineConfigWrite,
        list_cls=ExtractionPipelineConfigList,
        _write_list_cls=ExtractionPipelineConfigWriteList,
        methods={
            "create": [Method(api_class_method="create", mock_name="create_extraction_pipeline_config")],
            "retrieve": [
                Method(api_class_method="list", mock_name="return_values"),
                Method(api_class_method="retrieve", mock_name="return_value"),
            ],
        },
    ),
    APIResource(
        api_name="data_modeling.containers",
        resource_cls=Container,
        list_cls=ContainerList,
        _write_cls=ContainerApply,
        _write_list_cls=ContainerApplyList,
        methods={
            "create": [Method(api_class_method="apply", mock_name="create")],
            "delete": [Method(api_class_method="delete", mock_name="delete_data_modeling")],
            "retrieve": [
                Method(api_class_method="list", mock_name="return_values"),
                Method(api_class_method="retrieve", mock_name="return_values"),
            ],
        },
    ),
    APIResource(
        api_name="data_modeling.views",
        resource_cls=View,
        list_cls=ViewList,
        _write_cls=ViewApply,
        _write_list_cls=ViewApplyList,
        methods={
            "create": [Method(api_class_method="apply", mock_name="create")],
            "delete": [Method(api_class_method="delete", mock_name="delete_data_modeling")],
            "retrieve": [
                Method(api_class_method="list", mock_name="return_values"),
                Method(api_class_method="retrieve", mock_name="data_model_retrieve"),
            ],
        },
    ),
    APIResource(
        api_name="data_modeling.data_models",
        resource_cls=DataModel,
        list_cls=DataModelList,
        _write_cls=DataModelApply,
        _write_list_cls=DataModelApplyList,
        methods={
            "create": [Method(api_class_method="apply", mock_name="create")],
            "delete": [Method(api_class_method="delete", mock_name="delete_data_modeling")],
            "retrieve": [
                Method(api_class_method="list", mock_name="return_values"),
                Method(api_class_method="retrieve", mock_name="return_values"),
            ],
        },
    ),
    APIResource(
        api_name="data_modeling.spaces",
        resource_cls=Space,
        list_cls=SpaceList,
        _write_cls=SpaceApply,
        _write_list_cls=SpaceApplyList,
        methods={
            "create": [Method(api_class_method="apply", mock_name="create")],
            "delete": [Method(api_class_method="delete", mock_name="delete_space")],
            "retrieve": [
                Method(api_class_method="list", mock_name="return_values"),
                Method(api_class_method="retrieve", mock_name="return_values"),
            ],
        },
    ),
    APIResource(
        api_name="time_series.data",
        resource_cls=Datapoints,
        list_cls=DatapointsList,
        methods={
            "create": [
                Method(api_class_method="insert", mock_name="create"),
                Method(api_class_method="insert_dataframe", mock_name="insert_dataframe"),
            ],
        },
    ),
    APIResource(
        api_name="files",
        resource_cls=FileMetadata,
        list_cls=FileMetadataList,
        _write_cls=FileMetadataWrite,
        _write_list_cls=FileMetadataWriteList,
        methods={
            "create": [
                Method(api_class_method="upload", mock_name="upload"),
                Method(api_class_method="create", mock_name="create"),
                # This is used by functions to upload the file used for deployment.
                Method(api_class_method="upload_bytes", mock_name="upload_bytes_files_api"),
            ],
            "delete": [Method(api_class_method="delete", mock_name="delete_id_external_id")],
            "retrieve": [
                Method(api_class_method="list", mock_name="return_values"),
                Method(api_class_method="retrieve", mock_name="return_value"),
                Method(api_class_method="retrieve_multiple", mock_name="return_values"),
            ],
        },
    ),
    APIResource(
        api_name="data_modeling.instances",
        resource_cls=Node,
        list_cls=NodeList,
        _write_cls=NodeApply,
        _write_list_cls=NodeApplyList,
        methods={
            "create": [Method(api_class_method="apply", mock_name="create_instances")],
            "delete": [Method(api_class_method="delete", mock_name="delete_instances")],
            "retrieve": [
                Method(api_class_method="list", mock_name="return_values"),
                Method(api_class_method="retrieve", mock_name="return_values"),
            ],
        },
    ),
]