from __future__ import annotations

import itertools
import os
import re
import shutil
from collections import ChainMap, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal, overload

import yaml
from rich import print

from cognite_toolkit.cdf_tk.load import LOADER_BY_FOLDER_NAME
from cognite_toolkit.cdf_tk.utils import LoadWarning, validate_case_raw

# This is the default config located locally in each module.
DEFAULT_CONFIG_FILE = "default.config.yaml"
# The environment file:
ENVIRONMENTS_FILE = "environments.yaml"
# The local config file:
CONFIG_FILE = "config.yaml"
# The default package files
DEFAULT_PACKAGES_FILE = "default.packages.yaml"
# The package files:
PACKAGES_FILE = "packages.yaml"
TMPL_DIRS = ["common", "modules", "local_modules", "examples", "experimental"]
# Add any other files below that should be included in a build
EXCL_FILES = ["README.md", DEFAULT_CONFIG_FILE]
# Which suffixes to exclude when we create indexed files (i.e., they are bundled with their main config file)
EXCL_INDEX_SUFFIX = frozenset(["sql", "csv", "parquet"])
# Which suffixes to process for template variable replacement
PROC_TMPL_VARS_SUFFIX = frozenset([".yaml", ".yml", ".sql", ".csv", ".parquet", ".json", ".txt", ".md", ".html", ".py"])


def read_environ_config(
    root_dir: str = "./",
    build_env: str = "dev",
    tmpl_dirs: [str] = TMPL_DIRS,
    set_env_only: bool = False,
    verbose: bool = False,
) -> list[str]:
    """Read the global configuration files and return a list of modules in correct order.

    The presence of a module directory in tmpl_dirs is verified.
    Yields:
        List of modules in the order they should be processed.
        Exception(ValueError) if a module is not found in tmpl_dirs.
    """
    if not root_dir.endswith("/"):
        root_dir = root_dir + "/"
    tmpl_dirs = [root_dir + t for t in tmpl_dirs]
    global_config = read_yaml_files(root_dir, "default.packages.yaml")
    packages = global_config.get("packages", {})
    packages.update(read_yaml_files(root_dir, "packages.yaml").get("packages", {}))
    environment_config = read_yaml_files(root_dir, "local.yaml")

    print(f"  Environment is {build_env}, using that section in {ENVIRONMENTS_FILE}.\n")
    if verbose:
        print("  [bold green]INFO:[/] Found defined packages:")
        for name, content in packages.items():
            print(f"    {name}: {content}")
    modules = []
    if len(environment_config) == 0:
        return []
    try:
        defs = environment_config[build_env]
    except KeyError:
        raise ValueError(f"Environment {build_env} not found in local.yaml")

    os.environ["CDF_ENVIRON"] = build_env
    for k, v in defs.items():
        if k == "project":
            if os.environ.get("CDF_PROJECT", "<not set>") != v:
                if build_env == "dev" or build_env == "local" or build_env == "demo":
                    print(
                        f"  [bold yellow]WARNING:[/] Project name mismatch (CDF_PROJECT) between local.yaml ({v}) and what is defined in environment ({os.environ.get('CDF_PROJECT','<not_set>')})."
                    )
                    print(f"  Environment is {build_env}, continuing (would have stopped for staging and prod)...")
                else:
                    raise ValueError(
                        f"Project name mismatch (CDF_PROJECT) between local.yaml ({v}) and what is defined in environment ({os.environ['CDF_PROJECT']})."
                    )
        elif k == "type":
            os.environ["CDF_BUILD_TYPE"] = v
        elif k == "deploy":
            print(f"  [bold green]INFO:[/] Building module list for environment {build_env}...")
            for m in v:
                for g2, g3 in packages.items():
                    if m == g2:
                        if verbose:
                            print(f"    Including modules from package {m}: {g3}")
                        for m2 in g3:
                            if m2 not in modules:
                                modules.append(m2)
                    elif m not in modules and packages.get(m) is None:
                        if verbose:
                            print(f"    Including explicitly defined module {m}")
                        modules.append(m)
    if set_env_only:
        return []
    if len(modules) == 0:
        print(
            f"  [bold yellow]WARNING:[/] Found no defined modules in local.yaml, have you configured the environment ({build_env})?"
        )
    load_list = []
    module_dirs = {}
    for d in tmpl_dirs:
        if not module_dirs.get(d):
            module_dirs[d] = []
        try:
            for dirnames in Path(d).iterdir():
                module_dirs[d].append(dirnames.name)
        except Exception:
            ...
    for m in modules:
        found = False
        for dir, mod in module_dirs.items():
            if m in mod:
                load_list.append(f"{dir}/{m}")
                found = True
                break
        if not found:
            raise ValueError(f"Module {m} not found in template directories {tmpl_dirs}.")
    return load_list


def get_selected_modules(
    source_module: Path,
    environment_file: Path,
    build_env: str = "dev",
    verbose: bool = False,
) -> list[str]:
    print(f"  Environment is {build_env}, using that section in {ENVIRONMENTS_FILE!s}.\n")

    modules_by_package = _read_packages(source_module, verbose)

    selected_module_and_packages = _get_modules_and_packages(environment_file, build_env)

    selected_packages = [package for package in selected_module_and_packages if package in modules_by_package]
    if verbose:
        print("  [bold green]INFO:[/] Selected packages:")
        for package in selected_packages:
            print(f"    {package}")

    selected_modules = [module for module in selected_module_and_packages if module not in modules_by_package]
    selected_modules.extend(itertools.chain.from_iterable(modules_by_package[package] for package in selected_packages))

    if verbose:
        print("  [bold green]INFO:[/] Selected modules:")
        for module in selected_modules:
            print(f"    {module}")
    if not selected_modules:
        print(
            f"  [bold yellow]WARNING:[/] Found no defined modules in {ENVIRONMENTS_FILE!s}, have you configured the environment ({build_env})?"
        )
        exit(1)

    available_modules = {module.name for module, _ in iterate_modules(source_module)}
    if not (missing_modules := set(selected_modules) - available_modules):
        return selected_modules

    raise ValueError(f"Modules {missing_modules} not found in {source_module}.")


def _get_modules_and_packages(environment_file: Path, build_env: str) -> list[str]:
    environment_config = read_yaml_file(environment_file)
    environment = environment_config.get(build_env)
    if environment is None:
        raise ValueError(f"Environment {build_env} not found in {ENVIRONMENTS_FILE!s}")
    try:
        project_config = environment["project"]
        environment_type = environment["type"]
        deploy = environment["deploy"]
    except KeyError:
        raise ValueError(
            f"Environment {build_env} is missing required fields 'project', 'type', or 'deploy' in {ENVIRONMENTS_FILE!s}"
        ) from None

    os.environ["CDF_ENVIRON"] = build_env
    os.environ["CDF_BUILD_TYPE"] = environment_type
    if (project_env := os.environ.get("CDF_PROJECT", "<not set>")) != project_config:
        if build_env == "dev" or build_env == "local" or build_env == "demo":
            print(
                f"  [bold yellow]WARNING:[/] Project name mismatch (CDF_PROJECT) between {ENVIRONMENTS_FILE!s} ({project_config}) and what is defined in environment ({project_env})."
            )
            print(f"  Environment is {build_env}, continuing (would have stopped for staging and prod)...")
        else:
            raise ValueError(
                f"Project name mismatch (CDF_PROJECT) between {ENVIRONMENTS_FILE!s} ({project_config}) and what is defined in environment ({project_env=} != {project_config=})."
            )
    return deploy


def _read_packages(source_module, verbose):
    cdf_modules_by_packages = read_yaml_file(source_module / DEFAULT_PACKAGES_FILE).get("packages", {})
    if (package_path := source_module / PACKAGES_FILE).exists():
        local_modules_by_packages = read_yaml_file(package_path).get("packages", {})
        if overwrites := set(cdf_modules_by_packages.keys()) & set(local_modules_by_packages.keys()):
            print(
                f"  [bold yellow]WARNING:[/] Found modules in {PACKAGES_FILE} that are also defined in {DEFAULT_PACKAGES_FILE}:"
            )
            for module in overwrites:
                print(f"    {module}")
            print(f"  Using the modules defined in {PACKAGES_FILE}.")
        modules_by_package = {**cdf_modules_by_packages, **local_modules_by_packages}
    else:
        modules_by_package = cdf_modules_by_packages
    if verbose:
        print("  [bold green]INFO:[/] Found defined packages:")
        for name, content in modules_by_package.items():
            print(f"    {name}: {content}")
    return modules_by_package


def read_yaml_files(
    yaml_dirs: list[str] | str,
    name: str | None = None,
) -> dict[str, Any]:
    """Read all YAML files in the given directories and return a dictionary

    This function will not traverse into sub-directories.

    yaml_dirs: list of directories to read YAML files from
    name: (optional) name of the file(s) to read, either filename or regex. Defaults to config.yaml and default.config.yaml
    """

    if isinstance(yaml_dirs, str):
        yaml_dirs = [yaml_dirs]
    files = []
    if name is None:
        # Order is important!
        for directory in yaml_dirs:
            files.extend(Path(directory).glob("default.config.yaml"))
            files.extend(Path(directory).glob("config.yaml"))
    else:
        name = re.compile(f"^{name}")
        for directory in yaml_dirs:
            for file in Path(directory).glob("*.yaml"):
                if not (name.match(file.name)):
                    continue
                files.append(file)
    data = {}
    for yaml_file in files:
        try:
            config_data = yaml.safe_load(yaml_file.read_text())
        except yaml.YAMLError as e:
            print(f"  [bold red]ERROR:[/] reading {yaml_file}: {e}")
            continue
        data.update(config_data)
    return data


@overload
def read_yaml_file(filepath: Path, expected_output: Literal["dict"] = "dict") -> dict[str, Any]:
    ...


@overload
def read_yaml_file(filepath: Path, expected_output: Literal["list"]) -> list[dict[str, Any]]:
    ...


def read_yaml_file(
    filepath: Path, expected_output: Literal["list", "dict"] = "dict"
) -> dict[str, Any] | list[dict[str, Any]]:
    """Read a YAML file and return a dictionary

    filepath: path to the YAML file
    """
    try:
        config_data = yaml.safe_load(filepath.read_text())
    except yaml.YAMLError as e:
        print(f"  [bold red]ERROR:[/] reading {filepath}: {e}")
        return {}
    if expected_output == "list" and isinstance(config_data, dict):
        print(f"  [bold red]ERROR:[/] {filepath} is not a list")
        exit(1)
    elif expected_output == "dict" and isinstance(config_data, list):
        print(f"  [bold red]ERROR:[/] {filepath} is not a dict")
        exit(1)
    return config_data


def check_yaml_semantics(parsed: Any, filepath_src: Path, filepath_build: Path, verbose: bool = False) -> bool:
    """Check the yaml file for semantic errors

    parsed: the parsed yaml file
    filepath: the path to the yaml file
    yields: True if the yaml file is semantically acceptable, False if build should fail.
    """
    if parsed is None or filepath_src is None or filepath_build is None:
        return False
    resource_type = filepath_src.parts[-2]
    ext_id = None
    if resource_type == "data_models" and ".space." in filepath_src.name:
        ext_id = parsed.get("space")
        ext_id_type = "space"
    elif resource_type == "data_models" and ".node." in filepath_src.name:
        try:
            ext_ids = {source["source"]["externalId"] for node in parsed["nodes"] for source in node["sources"]}
        except KeyError:
            print(f"      [bold red]:[/] Node file {filepath_src} has invalid dataformat.")
            exit(1)
        if len(ext_ids) != 1:
            print(f"      [bold red]:[/] All nodes in {filepath_src} must have the same view.")
            exit(1)
        ext_id = ext_ids.pop()
        ext_id_type = "view.externalId"
    elif resource_type == "auth":
        ext_id = parsed.get("name")
        ext_id_type = "name"
    elif resource_type in ["data_sets", "timeseries", "files"] and isinstance(parsed, list):
        ext_id = ""
        ext_id_type = "multiple"
    elif resource_type == "raw":
        ext_id = f"{parsed.get('dbName')}.{parsed.get('tableName')}"
        if "None" in ext_id:
            ext_id = None
        ext_id_type = "dbName and/or tableName"
    else:
        ext_id = parsed.get("externalId") or parsed.get("external_id")
        ext_id_type = "externalId"

    if ext_id is None:
        print(
            f"      [bold yellow]WARNING:[/] the {resource_type} {filepath_src} is missing the {ext_id_type} field(s)."
        )
        return False
    if resource_type == "auth":
        parts = ext_id.split("_")
        if len(parts) < 2:
            if ext_id == "applications-configuration":
                if verbose:
                    print(
                        "      [bold green]INFO:[/] the group applications-configuration does not follow the recommended '_' based namespacing because Infield expects this specific name."
                    )
            else:
                print(
                    f"      [bold yellow]WARNING:[/] the group {filepath_src} has a name [bold]{ext_id}[/] without the recommended '_' based namespacing."
                )
        elif parts[0] != "gp":
            print(
                f"      [bold yellow]WARNING:[/] the group {filepath_src} has a name [bold]{ext_id}[/] without the recommended `gp_` based prefix."
            )
    elif resource_type == "transformations":
        # First try to find the sql file next to the yaml file with the same name
        sql_file1 = filepath_src.parent / f"{filepath_src.stem}.sql"
        if not sql_file1.exists():
            # Next try to find the sql file next to the yaml file with the external_id as filename
            sql_file2 = filepath_src.parent / f"{ext_id}.sql"
            if not sql_file2.exists():
                print("      [bold yellow]WARNING:[/] could not find sql file:")
                print(f"                 [bold]{sql_file1.name}[/] or ")
                print(f"                 [bold]{sql_file2.name}[/]")
                print(f"               Expected to find it next to the yaml file at {sql_file1.parent}.")
                return False
        parts = ext_id.split("_")
        if len(parts) < 2:
            print(
                f"      [bold yellow]WARNING:[/] the transformation {filepath_src} has an externalId [bold]{ext_id}[/] without the recommended '_' based namespacing."
            )
        elif parts[0] != "tr":
            print(
                f"      [bold yellow]WARNING:[/] the transformation {filepath_src} has an externalId [bold]{ext_id}[/] without the recommended 'tr_' based prefix."
            )
    elif resource_type == "data_models" and ext_id_type == "space":
        parts = ext_id.split("_")
        if len(parts) < 2:
            print(
                f"      [bold yellow]WARNING:[/] the space {filepath_src} has an externalId [bold]{ext_id}[/] without the recommended '_' based namespacing."
            )
        elif parts[0] != "sp":
            if ext_id == "cognite_app_data" or ext_id == "APM_SourceData" or ext_id == "APM_Config":
                if verbose:
                    print(
                        f"      [bold green]INFO:[/] the space {ext_id} does not follow the recommended '_' based namespacing because Infield expects this specific name."
                    )
            else:
                print(
                    f"      [bold yellow]WARNING:[/] the space {filepath_src} has an externalId [bold]{ext_id}[/] without the recommended 'sp_' based prefix."
                )
    elif resource_type == "extraction_pipelines":
        parts = ext_id.split("_")
        if len(parts) < 2:
            print(
                f"      [bold yellow]WARNING:[/] the extraction pipeline {filepath_src} has an externalId [bold]{ext_id}[/] without the recommended '_' based namespacing."
            )
        elif parts[0] != "ep":
            print(
                f"      [bold yellow]WARNING:[/] the extraction pipeline {filepath_src} has an externalId [bold]{ext_id}[/] without the recommended 'ep_' based prefix."
            )
    elif resource_type == "data_sets" or resource_type == "timeseries" or resource_type == "files":
        if not isinstance(parsed, list):
            parsed = [parsed]
        for ds in parsed:
            ext_id = ds.get("externalId") or ds.get("external_id")
            if ext_id is None:
                print(
                    f"      [bold yellow]WARNING:[/] the {resource_type} {filepath_src} is missing the {ext_id_type} field."
                )
                return False
            parts = ext_id.split("_")
            # We don't want to throw a warning on entities that should not be governed by the tool
            # in production (i.e. fileseries, files, and other "real" data)
            if resource_type == "data_sets" and len(parts) < 2:
                print(
                    f"      [bold yellow]WARNING:[/] the {resource_type} {filepath_src} has an externalId [bold]{ext_id}[/] without the recommended '_' based namespacing."
                )
    return True


def process_config_files(
    source_module_dir: Path,
    selected_modules: list[str],
    build_dir: Path,
    config: dict[str, Any],
    build_env: str = "dev",
    verbose: bool = False,
) -> None:
    configs = split_config(config)
    number_by_resource_type = defaultdict(int)

    for module_dir, filepaths in iterate_modules(source_module_dir):
        if module_dir.name not in selected_modules:
            continue
        if verbose:
            print(f"  [bold green]INFO:[/] Processing module {module_dir.name}")
        local_config = create_local_config(configs, module_dir)
        # Sort to support 1., 2. etc prefixes
        filepaths.sort()
        for filepath in filepaths:
            if verbose:
                print(f"    [bold green]INFO:[/] Processing {filepath.name}")

            if filepath.suffix.lower() not in PROC_TMPL_VARS_SUFFIX:
                # Copy the file as is, not variable replacement
                destination = build_dir / filepath.parent.name / filepath.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(filepath, destination)
                continue

            content = filepath.read_text()
            content = replace_variables(content, local_config, build_env)
            filename = create_file_name(filepath, number_by_resource_type)

            destination = build_dir / filepath.parent.name / filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content)

            validate(content, destination, filepath)


def build_config(
    build_dir: Path,
    source_dir: Path,
    config_file: Path,
    environment_file: Path,
    build_env: str = "dev",
    clean: bool = False,
    verbose: bool = False,
):
    if build_env is None:
        raise ValueError("build_env must be specified")
    if build_dir.exists():
        if any(build_dir.iterdir()):
            if clean:
                shutil.rmtree(build_dir)
                build_dir.mkdir()
                print(f"  [bold green]INFO:[/] Cleaned existing build directory {build_dir!s}.")
            else:
                print("  [bold yellow]WARNING:[/] Build directory is not empty. Use --clean to remove existing files.")
    else:
        build_dir.mkdir()
    source_module_dir = source_dir / "cdf_modules"

    selected_modules = get_selected_modules(source_module_dir, environment_file, build_env, verbose)

    config = read_yaml_file(config_file)
    process_config_files(source_module_dir, selected_modules, build_dir, config, build_env, verbose)


def generate_warnings_report(load_warnings: list[LoadWarning], indent: int = 0) -> str:
    report = [""]
    for (file, identifier, id_name), file_warnings in itertools.groupby(
        sorted(load_warnings), key=lambda w: (w.filepath, w.id_value, w.id_name)
    ):
        report.append(f"{'    '*indent}In File {str(file)!r}")
        report.append(f"{'    '*indent}In entry {id_name}={identifier!r}")
        for warning in file_warnings:
            report.append(f"{'    '*(indent+1)}{warning!s}")

    return "\n".join(report)


def generate_config(directory: Path, include_modules: set[str] | None = None) -> dict[str, Any]:
    """Generate a config dictionary from the default.config.yaml files in the given directories.

    You can specify a set of modules to include in the config. If you do not specify any modules, all modules will be included.

    Args:
        directory: A root directory to search for default.config.yaml files.
        include_modules: A set of modules to include in the config. If None, all modules will be included.

    Returns:
        A config dictionary.
    """
    config: dict[str, Any] = {}
    if not directory.exists():
        raise ValueError(f"Directory {directory} does not exist")
    defaults = sorted(directory.glob(f"**/{DEFAULT_CONFIG_FILE}"), key=lambda f: f.relative_to(directory))
    for default_config in defaults:
        if include_modules is not None and default_config.parent.name not in include_modules:
            continue
        parts = default_config.relative_to(directory).parent.parts
        if len(parts) == 1:
            # This is a root config file
            config.update(yaml.safe_load(default_config.read_text()))
            continue
        local_config = config
        for key in parts[:-1]:
            local_config = local_config.setdefault(key, {})
        local_config[parts[-1]] = yaml.safe_load(default_config.read_text())

    return config


def iterate_modules(root_dir: Path) -> tuple[Path, list[Path]]:
    for module_dir in root_dir.rglob("*"):
        if not module_dir.is_dir():
            continue
        module_directories = [path for path in module_dir.iterdir() if path.is_dir()]
        is_all_resource_directories = all(dir.name in LOADER_BY_FOLDER_NAME for dir in module_directories)
        if module_directories and is_all_resource_directories:
            yield module_dir, [path for path in module_dir.rglob("*") if path.is_file() and path.name not in EXCL_FILES]


def create_local_config(config: dict[str, Any], module_dir: Path) -> Mapping[str, str]:
    maps = []
    parts = module_dir.parts
    if parts[0] != "cdf_modules":
        parts = parts[parts.index("cdf_modules") :]
    for no in range(len(parts), -1, -1):
        if c := config.get(".".join(parts[:no])):
            maps.append(c)
    return ChainMap(*maps)


def split_config(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    configs = {}
    _split_config(config, configs, prefix="")
    return configs


def _split_config(config: dict[str, Any], configs: dict[str, dict[str, str]], prefix: str = "") -> None:
    for key, value in config.items():
        if isinstance(value, dict):
            if prefix and not prefix.endswith("."):
                prefix = f"{prefix}."
            _split_config(value, configs, prefix=f"{prefix}{key}")
        else:
            configs.setdefault(prefix, {})[key] = value


def create_file_name(filepath: Path, number_by_resource_type: dict[str, int]) -> str:
    filename = filepath.name
    if filepath.suffix in EXCL_INDEX_SUFFIX:
        return filename
    # Get rid of the local index
    filename = re.sub("^[0-9]+\\.", "", filename)
    number_by_resource_type[filepath.parent.name] += 1
    filename = f"{number_by_resource_type[filepath.parent.name]}.{filename}"
    return filename


def replace_variables(content: str, local_config: Mapping[str, str], build_env: str) -> str:
    for name, variable in local_config.items():
        if "." in name:
            # If the key has a dot, it is a build_env specific variable.
            # Skip if it's the wrong environment.
            env, name = name.split(".", 1)
            if env != build_env:
                continue
        content = content.replace(f"{{{{{name}}}}}", str(variable))
    return content


def validate(content: str, destination: Path, source_path: Path) -> None:
    for unmatched in re.findall(pattern=r"\{\{.*?\}\}", string=content):
        print(f"  [bold yellow]WARNING:[/] Unresolved template variable {unmatched} in {destination!s}")

    if destination.suffix in {".yaml", ".yml"}:
        try:
            parsed = yaml.safe_load(content)
        except yaml.YAMLError as e:
            print(
                f"  [bold red]ERROR:[/] YAML validation error for {destination.name} after substituting config variables: \n{e}"
            )
            exit(1)

        if isinstance(parsed, dict):
            parsed = [parsed]
        for item in parsed:
            if not check_yaml_semantics(
                parsed=item,
                filepath_src=source_path,
                filepath_build=destination,
            ):
                exit(1)
        loader = LOADER_BY_FOLDER_NAME.get(destination.parent.name)
        if len(loader) == 1:
            loader = loader[0]
        else:
            loader = next((loader for loader in loader if re.match(loader.filename_pattern, destination.stem)), None)
        if loader:
            load_warnings = validate_case_raw(
                parsed, loader.resource_cls, destination, identifier_key=loader.identifier_key
            )
            if load_warnings:
                print(f"  [bold yellow]WARNING:[/]{generate_warnings_report(load_warnings, indent=1)}")
