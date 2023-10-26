from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

import yaml

# Directory paths for YAML files
YAML_DIRS = ["./"]
TMPL_DIRS = ["./common", "./modules"]
# Add any other files below that should be included in a build
EXCL_FILES = ["README.md"]
# Which suffixes to exclude when we create indexed files (i.e. they are bundled with their main config file)
EXCL_INDEX_SUFFIX = ["sql"]


def read_environ_config(
    root_dir: str = "./",
    build_env: str = "dev",
    tmpl_dirs: str = TMPL_DIRS,
) -> list[str]:
    """Read the global configuration files and return a list of modules in correct order.

    The presence of a module directory in tmpl_dirs is verified.
    Yields:
        List of modules in the order they should be processed.
        Exception(ValueError) if a module is not found in tmpl_dirs.
    """
    global_config = read_yaml_files(root_dir, "global.yaml")
    local_config = read_yaml_files(root_dir, "local.yaml")
    print(f"Environment is {build_env}, using that section in local.yaml.\n")
    modules = []

    try:
        defs = local_config[build_env]
    except KeyError:
        raise ValueError(f"Environment {build_env} not found in local.yaml")

    os.environ["CDF_ENVIRON"] = build_env
    for k, v in defs.items():
        if k == "project":
            if os.environ["CDF_PROJECT"] != v:
                if build_env == "dev" or build_env == "local":
                    print(
                        f"WARNING!!! Project name mismatch (CDF_PROJECT) between local.yaml ({v}) and what is defined in environment ({os.environ['CDF_PROJECT']})."
                    )
                    print(f"Environment is {build_env}, continuing...")
                else:
                    raise ValueError(
                        f"Project name mismatch (CDF_PROJECT) between local.yaml ({v}) and what is defined in environment ({os.environ['CDF_PROJECT']})."
                    )
        elif k == "type":
            os.environ["CDF_BUILD_TYPE"] = v
        elif k == "deploy":
            for m in v:
                for g2, g3 in global_config.get("packages", {}).items():
                    if m == g2:
                        for m2 in g3:
                            if m2 not in modules:
                                modules.append(m2)
                    elif m not in modules and global_config.get("packages", {}).get(m) is None:
                        modules.append(m)

    if len(modules) == 0:
        print(f"WARNING! Found no defined modules in local.yaml, have you configured the environment ({build_env})?")
    load_list = []
    module_dirs = {}
    for d in tmpl_dirs:
        if not module_dirs.get(d):
            module_dirs[d] = []
        for dirnames in os.listdir(d):
            module_dirs[d].append(dirnames)
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


def read_yaml_files(yaml_dirs, name: str = "config.yaml"):
    """Read all YAML files in the given directories and return a dictionary

    This function will not traverse into sub-directories.

    yaml_dirs: list of directories to read YAML files from
    """

    data = {}
    for directory in yaml_dirs:
        for yaml_file in Path(directory).glob(name):
            try:
                config_data = yaml.safe_load(yaml_file.read_text())
            except yaml.YAMLError:
                print(f"Error reading {yaml_file}")
                continue
            data.update(config_data)
    # Replace env variables of ${ENV_VAR} with actual value from environment
    for k, v in os.environ.items():
        for k2, v2 in data.items():
            if f"${{{k}}}" in v2:
                if isinstance(data[k2], list):
                    for i in range(len(data[k2])):
                        data[k2][i] = data[k2][i].replace(f"${{{k}}}", v)
                else:
                    data[k2] = data[k2].replace(f"${{{k}}}", v)
    return data


def process_config_files(
    dirs: [str],
    yaml_data: str,
    build_dir: str = "./build",
    build_env: str = "dev",
    clean: bool = False,
):
    path = Path(build_dir)
    if path.exists():
        if any(path.iterdir()):
            if clean:
                shutil.rmtree(path)
                path.mkdir()
            else:
                print("Warning: Build directory is not empty. Use --clean to remove existing files.")
    else:
        path.mkdir()

    local_yaml_path = ""
    yaml_local = {}
    indices = {}
    for directory in dirs:
        for dirpath, _, filenames in os.walk(directory):
            # Sort to support 1., 2. etc prefixes
            filenames.sort()
            # When we have traversed out of the module, reset the local yaml config
            if local_yaml_path not in dirpath:
                local_yaml_path == ""
                yaml_local = {}
            for file in filenames:
                if file in EXCL_FILES:
                    continue
                # Skip the config.yaml file
                if file == "config.yaml":
                    # Pick up this local yaml files
                    local_yaml_path = dirpath
                    yaml_local = read_yaml_files([dirpath])
                    continue
                with open(dirpath + "/" + file) as f:
                    content = f.read()
                # Replace the local yaml variables
                for k, v in yaml_local.items():
                    if "." in k:
                        # If the key has a dot, it is a build_env specific variable.
                        # Skip if it's the wrong environment.
                        if k.split(".")[0] != build_env:
                            continue
                        k = k.split(".", 2)[1]
                    # assuming template variables are in the format {{key}}
                    # TODO: issue warning if key is not found, this can indicate a config file error
                    content = content.replace(f"{{{{{k}}}}}", str(v))
                # Replace the root yaml variables
                for k, v in yaml_data.items():
                    if "." in k:
                        # If the key has a dot, it is a build_env specific variable.
                        # Skip if it's the wrong environment.
                        if k.split(".")[0] != build_env:
                            continue
                        k = k.split(".", 2)[1]
                    # assuming template variables are in the format {{key}}
                    content = content.replace(f"{{{{{k}}}}}", str(v))

                for unmatched in re.findall(pattern=r"\{\{.*?\}\}", string=content):
                    print(f"WARNING: Unmatched template variable {unmatched} in {dirpath}/{file}")

                split_path = dirpath.split("/")
                cdf_path = split_path[len(split_path) - 1]
                new_path = Path(f"{build_dir}/{cdf_path}")
                new_path.mkdir(exist_ok=True, parents=True)
                # For .sql and other dependent files, we do not prefix as we expect them
                # to be named with the external_id of the entitiy they are associated with.
                if file.split(".")[-1] not in EXCL_INDEX_SUFFIX:
                    if not indices.get(cdf_path):
                        indices[cdf_path] = 1
                    else:
                        indices[cdf_path] += 1
                    # Get rid of the local index
                    if re.match("^[0-9]+\\.", file):
                        file = file.split(".", 1)[1]
                    # If we are processing raw tables, we want to pick up the raw_db config.yaml
                    # variable to determine the database name.
                    if dirpath.split("/")[-1] == "raw":
                        file = f"{indices[cdf_path]}.{yaml_local.get('raw_db', 'default')}.{file}"
                    else:
                        file = f"{indices[cdf_path]}.{file}"
                with open(new_path / file, "w") as f:
                    f.write(content)


def build_config(dir: str = "./build", build_env: str = "dev", clean: bool = False):
    if build_env is None:
        raise ValueError("build_env must be specified")
    modules = read_environ_config(root_dir="./", tmpl_dirs=TMPL_DIRS, build_env=build_env)
    process_config_files(
        dirs=modules,
        yaml_data=read_yaml_files(yaml_dirs=YAML_DIRS),
        build_dir=dir,
        build_env=build_env,
        clean=clean,
    )
