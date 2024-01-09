from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from cognite_toolkit.cdf_tk.templates import (
    COGNITE_MODULES,
    _dump_yaml_with_comments,
    _extract_comments,
    create_local_config,
    generate_config,
    split_config,
)

BUILD_CONFIG = Path(__file__).parent / "project_for_test"


def dict_keys(d: dict[str, Any]) -> set[str]:
    keys = set()
    for k, v in d.items():
        keys.add(k)
        if isinstance(v, dict):
            keys.update(dict_keys(v))
    return keys


def generate_config_test_cases():
    expected = {
        COGNITE_MODULES: {
            "a_module": {
                "readwrite_source_id": "<change_me>",
                "readonly_source_id": "<change_me>",
            },
            "another_module": {
                "default_location": "oid",
                "source_asset": "workmate",
                "source_workorder": "workmate",
                "source_files": "fileshare",
                "source_timeseries": "pi",
            },
            "top_variable": "<top_variable>",
            "parent_module": {"child_module": {"child_variable": "<change_me>"}},
        },
    }

    yield pytest.param(expected, None, id="Include all")

    only_a_module = {
        COGNITE_MODULES: {
            "a_module": {
                "readwrite_source_id": "<change_me>",
                "readonly_source_id": "<change_me>",
            },
        }
    }
    yield pytest.param(only_a_module, {"a_module"}, id="Include one module")


@pytest.fixture(scope="session")
def config_yaml() -> str:
    return (BUILD_CONFIG / "config.yaml").read_text()


class TestGenerateConfig:
    @pytest.mark.parametrize(
        "expected, include",
        list(generate_config_test_cases()),
    )
    def test_generate_partial(self, expected: str, include: set[str] | None) -> None:
        actual, _ = generate_config(BUILD_CONFIG, include_modules=include)

        assert yaml.safe_load(actual) == expected

    def test_generate_with_comments(self, config_yaml) -> None:
        expected_keys = dict_keys(yaml.safe_load(config_yaml))

        actual, _ = generate_config(BUILD_CONFIG)

        actual_keys = dict_keys(yaml.safe_load(actual))
        missing = expected_keys - actual_keys
        assert not missing, f"Missing keys: {missing}"
        extra = actual_keys - expected_keys
        assert not extra, f"Extra keys: {extra}"

    def test_generate_persist_variable_with_comment(self, config_yaml: str) -> None:
        custom_comment = "This is an extra comment added to the config only 'lore ipsum'"

        actual, difference = generate_config(BUILD_CONFIG, existing_config=config_yaml)

        loaded = yaml.safe_load(actual)
        assert loaded["cognite_modules"]["another_module"]["source_asset"] == "my_new_workmate"
        assert custom_comment in actual


@pytest.fixture()
def my_config():
    return {
        "top_variable": "my_top_variable",
        "module_a": {
            "readwrite_source_id": "my_readwrite_source_id",
            "readonly_source_id": "my_readonly_source_id",
        },
        "parent": {"child": {"child_variable": "my_child_variable"}},
    }


def test_split_config(my_config: dict[str, Any]) -> None:
    expected = {
        "": {"top_variable": "my_top_variable"},
        "module_a": {
            "readwrite_source_id": "my_readwrite_source_id",
            "readonly_source_id": "my_readonly_source_id",
        },
        "parent.child": {"child_variable": "my_child_variable"},
    }
    actual = split_config(my_config)

    assert actual == expected


def test_create_local_config(my_config: dict[str, Any]):
    configs = split_config(my_config)

    local_config = create_local_config(configs, Path("parent/child/auth/"))

    assert dict(local_config.items()) == {"top_variable": "my_top_variable", "child_variable": "my_child_variable"}


@pytest.mark.parametrize(
    "raw_file, key_prefix, expected_comments",
    [
        pytest.param(
            """# This is a module comment
variable: value # After variable comment
# Before variable comment
variable2: value2
variable3: 'value with #in it'
variable4: "value with #in it" # But a comment after
""",
            tuple("super_module.module_a".split(".")),
            {
                ("super_module", "module_a"): {"above": ["This is a module comment"], "after": []},
                ("super_module", "module_a", "variable"): {"above": [], "after": ["After variable comment"]},
                ("super_module", "module_a", "variable2"): {"above": ["Before variable comment"], "after": []},
                ("super_module", "module_a", "variable4"): {"above": [], "after": ["But a comment after"]},
            },
            id="module comments",
        )
    ],
)
def test_extract_comments(raw_file: str, key_prefix: tuple[str, ...], expected_comments: dict[str, Any]):
    actual_comments = _extract_comments(raw_file, key_prefix)
    assert actual_comments == expected_comments


@pytest.mark.parametrize(
    "config, comments, expected",
    [
        pytest.param(
            {
                "top_variable": "my_top_variable",
                "module_a": {
                    "readwrite_source_id": "my_readwrite_source_id",
                    "readonly_source_id": "my_readonly_source_id",
                },
                "parent": {"child": {"child_variable": "my_child_variable"}},
            },
            {
                tuple(): {"above": ["This is a module comment"], "after": []},
                ("top_variable",): {"above": [], "after": ["After variable comment"]},
                ("module_a",): {"above": ["Before variable comment"], "after": []},
                ("parent", "child", "child_variable"): {"above": [], "after": ["With a comment after"]},
            },
            """# This is a module comment
top_variable: my_top_variable # After variable comment
# Before variable comment
module_a:
  readwrite_source_id: my_readwrite_source_id
  readonly_source_id: my_readonly_source_id

parent:
  child:
    child_variable: my_child_variable # With a comment after
""",
            id="Config with comments",
        )
    ],
)
def test_dump_yaml_with_comments(config: dict[str, Any], comments: dict[tuple[str, ...], Any], expected: str):
    actual = _dump_yaml_with_comments(config, comments)

    assert actual == expected
