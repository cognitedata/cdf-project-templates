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
from ._base_loaders import Loader
from ._data_loaders import DatapointsLoader
from ._functions import DeployResult, DeployResults, clean_resources, deploy_resources
from ._resource_loaders import (
    AuthLoader,
    ContainerLoader,
    DataModelLoader,
    DataSetsLoader,
    ExtractionPipelineConfigLoader,
    ExtractionPipelineLoader,
    FileLoader,
    NodeLoader,
    RawLoader,
    SpaceLoader,
    TimeSeriesLoader,
    TransformationLoader,
    TransformationScheduleLoader,
    ViewLoader,
)

LOADER_BY_FOLDER_NAME: dict[str, list[type[Loader]]] = {}
for _loader in Loader.__subclasses__():
    if _loader.folder_name not in LOADER_BY_FOLDER_NAME:
        LOADER_BY_FOLDER_NAME[_loader.folder_name] = []
    # MyPy bug: https://github.com/python/mypy/issues/4717
    LOADER_BY_FOLDER_NAME[_loader.folder_name].append(_loader)  # type: ignore[type-abstract]
del _loader  # cleanup module namespace

__all__ = [
    "LOADER_BY_FOLDER_NAME",
    "AuthLoader",
    "NodeLoader",
    "DataModelLoader",
    "DataSetsLoader",
    "TimeSeriesLoader",
    "deploy_resources",
    "clean_resources",
    "DeployResult",
    "DeployResults",
    "TransformationLoader",
    "TransformationScheduleLoader",
    "ExtractionPipelineLoader",
    "RawLoader",
    "ExtractionPipelineConfigLoader",
    "FileLoader",
    "SpaceLoader",
    "ContainerLoader",
    "ViewLoader",
    "DatapointsLoader",
]
