from __future__ import annotations

import datetime

from cognite.client.data_classes.aggregations import Count
from cognite.client.data_classes.data_modeling import (
    DirectRelation,
    DirectRelationReference,
    MappedProperty,
    SingleHopConnectionDefinition,
)
from rich import print
from rich.table import Table

from .utils import CDFToolConfig


def describe_datamodel(ToolGlobals: CDFToolConfig, space_name: str, model_name: str | None) -> None:
    """Describe data model from CDF"""

    print(f"Describing data model ({model_name}) in space ({space_name})...")
    print("Verifying access rights...")
    client = ToolGlobals.verify_client(
        capabilities={
            "dataModelsAcl": ["READ", "WRITE"],
            "dataModelInstancesAcl": ["READ", "WRITE"],
        }
    )
    table = Table(title=f"Space {space_name}")
    table.add_column("Info", justify="left")
    table.add_column("Value", justify="left", style="green")
    try:
        space = client.data_modeling.spaces.retrieve(space_name)
    except Exception as e:
        print(f"Failed to retrieve space {space_name}.")
        print(e)
    else:
        if space is None:
            print(f"Failed to retrieve space {space_name}. It does not exists or you do not have access to it.")
        else:
            table.add_row("Name", str(space.name))
            table.add_row("Description", str(space.description))
            table.add_row("Created time", str(datetime.datetime.fromtimestamp(space.created_time / 1000)))
            table.add_row("Last updated time", str(datetime.datetime.fromtimestamp(space.last_updated_time / 1000)))
    try:
        containers = client.data_modeling.containers.list(space=space_name, include_global=True, limit=None)
    except Exception as e:
        print(f"Failed to retrieve containers for data model {model_name}.")
        print(e)
        return None
    containers_str = "\n".join([c.external_id for c in containers])
    table.add_row(f"Containers ({len(containers)})", "".join(containers_str))
    print(table)
    try:
        data_models = client.data_modeling.data_models.list(
            space=space_name, include_global=True, inline_views=True, limit=None
        )
    except Exception as e:
        print(f"Failed to retrieve data model {model_name} in space {space_name}.")
        print(e)
        return None
    if len(data_models) == 0:
        print(f"Failed to retrieve data model {model_name} in space {space_name}.")
        return None
    data_model = data_models[0]
    model_name = data_model.name or data_model.external_id
    if len(data_models) > 1:
        print(f"Found {len(data_models)} data models in space {space_name}.")
        print(f"  Only describing the first one ({model_name}).")
        print("  Use the --data-model flag to specify which data model to describe.")

    table = Table(title=f"Data model {model_name} in space {space_name}")
    table.add_column("Info", justify="right")
    table.add_column("Value", justify="left", style="green")
    table.add_row("Description", str(data_model.description))
    table.add_row(
        "Version",
        str(data_model.version),
    )
    table.add_row(
        "Global",
        "True" if data_model.is_global else "False",
    )
    table.add_row("Created time", str(datetime.datetime.fromtimestamp(data_model.created_time / 1000)))
    table.add_row("Last updated time", str(datetime.datetime.fromtimestamp(data_model.last_updated_time / 1000)))
    views = data_model.views
    table.add_row("Number of views", str(len(views)))
    view_names = "\n".join([v.external_id for v in views])
    table.add_row("List of views", "".join(view_names))
    print(table)
    model_edge_types: list[DirectRelationReference] = []
    for view in views:
        table = Table(title=f"View {view.external_id}, version {view.version} in space {space_name}")
        table.add_column("Info", justify="left")
        table.add_column("Value", justify="left", style="green")
        table.add_row("Number of properties", str(len(view.properties)))
        table.add_row("Used for", str(view.used_for))

        implements_str = "\n".join([i.external_id for i in view.implements or []])
        table.add_row("Implements", implements_str)
        properties = "\n".join(view.properties.keys())
        table.add_row("List of properties", "".join(properties))
        direct_relations = []
        edge_relations = []
        for p, edge_type in view.properties.items():
            if isinstance(edge_type, MappedProperty) and type(edge_type.type) is DirectRelation:
                if edge_type.source is None:
                    direct_relations.append(f"{p} --> no source")
                else:
                    direct_relations.append(
                        f"{p} --> ({edge_type.source.space}, {edge_type.source.external_id}, {edge_type.source.version})"
                    )
            elif isinstance(edge_type, SingleHopConnectionDefinition):
                edge_relations.append(
                    f"{p} -- {edge_type.direction} --> ({edge_type.source.space}, {edge_type.source.external_id}, {edge_type.source.version})"
                )
                model_edge_types.append(edge_type.type)
        nr_of_direct_relations = len(direct_relations)
        nr_of_edge_relations = len(edge_relations)
        table.add_row(f"Direct relations({nr_of_direct_relations})", "\n".join(direct_relations))
        table.add_row(f"Edge relations({nr_of_edge_relations})", "\n".join(edge_relations))
        node_count = 0
        # Iterate over all the nodes in the view 1,000 at the time
        try:
            result = client.data_modeling.instances.aggregate(
                view.as_id(),
                aggregates=Count("externalId"),
                instance_type="node",
            )
            node_count = int(result.value)
        except Exception as e:
            print(f"Failed to retrieve nodes for view {view.external_id} version {view.version} in space {view.space}.")
            print(e)
        table.add_row("Number of nodes", f"{node_count:,}")
        print(table)
