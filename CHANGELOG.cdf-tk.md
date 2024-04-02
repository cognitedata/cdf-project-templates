# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Changes are grouped as follows:

- `Added` for new features.
- `Changed` for changes in existing functionality.
- `Deprecated` for soon-to-be removed features.
- `Improved` for transparent changes, e.g. better performance.
- `Removed` for now removed features.
- `Fixed` for any bug fixes.
- `Security` in case of vulnerabilities.

## TBD

### Added

- Variables can now have extra spaces between curly braces and the variable name. For example, `{{  my_variable }}` is now
  a valid variable. Before this change, you would have to write `{{my_variable}}`.

### Fixed

- When running `cdf-tk` with a Token for initialization, the `cdf-tk` would raise an `IndexError`. This is now fixed.
- Container resources that did not have set the optional property `usedFor` would always be classified as changed,
  when, for example, running `cdf-tk deploy --dry-run`. This is now fixed.

### Changed

- The `cognite-modules` directory is no longer required. This enables the user to delete all templates and example
  modules and only use the `cognite-toolkit` CLI as a standalone.
- If two modules have the same name, the `cdf-tk build` command will now stop and raise an error. Before this change,
  the `cdf-tk build` command would continue and overwrite the first module with the second module.

### Changed

- The `cognite-modules` directory is no longer required. This enables the user to delete all templates and example
  modules and only use the `cognite-toolkit` CLI as a standalone.

## [0.2.0a1] - 2024-03-20

### Added

- Support for interactive login. The user can now set `LOGIN_FLOW=interactive` in the `.env` file
  to use interactive login.

### Changed

- The verification of access by the tool is now scoped to the resources that are being deployed instead of
  the entire project. This means that if the user only has access to a subset of the resources in the project,
  the tool will still be able to deploy those resources.

## [0.1.2] - 2024-03-18

### Fixed

- Running the command `cdf-tk auth verify --interactive` without a `.env` would raise a
  `AttributeError: 'CDFToolConfig' object has no attribute '_client'` error. This is now fixed and instead the user
  gets a guided experience to set up the `.env` file.

### Changed

- `cognite-toolkit` have moved the upper bound on the `cognite-sdk` dependency from `7.27` to `8.0`.
- Creating/Removing `spaces` no longer requires `DataModelingInstances` capability.

## [0.1.1] - 2024-03-01

### Fixed

- When running `cdf-tk clean` or `cdf-tk deploy --drop-data` for a data model with more than 10 containers,
  the command would raise an APIError. This is now fixed.
- A few minor potential `AttributeError` and `KeyError` bugs have been fixed.

## [0.1.0] - 2024-02-29

### Added

- Command `cdf-tk dump datamodel` for dumping data models from CDF into a local folder. The use case for this is to
  dump an existing data model from CDF and use it as a basis for building a new custom module with that data model.
- A Python package API for the cdf-tk. This allows for programmatic access to the cdf-tk functionality. This
  is limited to the `build` and `deploy` functionality. You can start by `from cognite_toolkit import CogniteToolkit`.

### Fixed

- In the function deployment, the hashing function used of the directory was independent of the location of the files
  within the function directory. This caused moving files not to trigger a redeployment of the function. This is now
  fixed.

### Changed

- Removed unused dependencies `mypy`, `pyarrow` and `chardet` from `cognite-toolkit` package.
- Lowered the required version of `pandas` to `1.5.3` in the `cognite-toolkit` package.

## [0.1.0b9] - 2024-02-20

### Added

- Introduced `cdf-tk pull transformation` and `cdf-tk pull node` commands to pull transformation or nodes
  from CDF to the local module.
- Support for using a template for file names `name: prefix_$FILENAME_suffix` in the `files` resource. The files will
  be processed and renamed as part of the build step.

### Fixed

- Fixed a bug that caused `Group` upsert to leave duplicate Groups
- Fixed issue with `run function --local` that did not pick up functions in modules without config variables.
- Fixed error when running `run function --local` on a function without all optional parameters for handle() being set.
- Bug when `cdf-tk deploy` of `ExtractionPipelineConfig` with multiple `config` objects in the same file.
  Then only the first `config` object was deployed. This is now fixed.

### Changed

- `cdf-tk` now uses --external-id consistently instead of --external_id.
- Removed upper limit on Python version requirement, such that, for example, `Python 3.12` is allowed. Note
  that when working with `functions` it is recommended to use `Python 3.9-3.11` as `Python 3.12` is not
  supported yet.
- `cdf-tk deploy`/`cdf-tk clean` now deploys all config files in one go, instead of one by one. This means batching
  is no longer done based on the number of resource files, but instead based on the limit of the CDF API.
- Files in module directories that do not live in a recognised resource directory will be skipped when building. If
  verbose is enabled, a warning will be printed for each skipped file.
- Only .yaml files in functions resource folders and the defined function sub-directories will be processed as part of
  building.

## [0.1.0b8] - 2024-02-14

### Added

- `Group` resource type supports list of groups in the same file

### Fixed

- `View` which implements other views would always be classified as changed, ven though no change
  has been done to the `view`, in the `cdf-tk deploy` command. This is now fixed.
- `DataModels` which are equal would be wrongly classified as changed if the view order was different.
  This is now fixed.
- In the `cdf-tk build`, modules with a nested folder structure under the resource folder were not built correctly.
  For example, if you had `my_module/data_models/container/my_container.container.view`, it would be put inside
  a `build/container/my_container.container.yaml` instead of `build/data_models/my_container.container.yaml`,
  and thus fail in the `cdf-tk deploy/clean` step. This is now fixed.
- When running `cdf-tk deploy` the prefixed number on resource file was not used to sort the deployment order.
  This is now fixed.
- Fixed a bug that caused Extraction Pipeline Config update to fail

## [0.1.0b7] - 2024-02-07

### Added

**NOTE: The function changelog was by accident included in beta6 and has been moved to the correct version.**

- Added support for loading functions and function schedules. Example of a function can be found in `cognite_modules/example/cdf_functions_dummy`.
- Added support for common function code as defined by `common_function_code` parameter in the environment config file.
- Added support for new command, `run function` that runs a function with a one-shot session created using currently
  configured credentials for cdf-tk.
- Added support for running a Cognite function locally using the `run function --local` command. This command will run the
  function locally in a virtual environment simulating CDF hosted run-time environment and print the result to the console.

### Changed

- **BREAKING:** The cdf-toolkit now requires one `config.yaml` per environment, for example, `config.dev.yaml` and `config.prod.yaml`.
- **BREAKING:** The file `environments.yaml` has been merged into `config.[env].yaml`.
  This means that the `environments.yaml` file is no longer used and the `config.[env].yaml`
  file now contains all the information needed to deploy to that environment.
- The module `cognite_modules` is no longer considered to be a black box governed by the toolkit, but should instead
  be controlled by the user. There are two main changes to the `cognite_modules` folder:
  - All `default.config.yaml` are removed from `cognite_modules` and only used when running `cdf-tk init`to generate
    `config.[env].yaml` files.
  - The file `default.packages.yaml` has been renamed `_system.yaml` and extended to include the `cdf-tk` version.
    This should not be changed by the user and is used to store package information for the toolkit itself and
    version.
- Running the `cdf-tk init --upgrade` now gives the user instructions on how to update the breaking changes
  since their last upgrade.
- If the user has changed any files in `cognite_modules`, the command `cdf-tk init --upgrade` will no longer
  overwrite the content of the `cognite_modules` folder. Instead, the user will be given instructions on how to
  update the `cognite_modules` files in the folder manually.

### Fixed

- In the generation of the `config.[env].yaml` multiline comments were lost. This is now fixed.

## [0.1.0b6] - 2024-01-25

### Added

- In `raw` resources, a RAW database or tables can be specified without data. Example, of a single database

 ```yaml
dbName: RawDatabase
```

or a database with table, no need to also specify a `.csv` or `.parquet` file for the table as was necessary before.

```yaml
dbName: myRawRawDatabase
tableName: myRawTable
```

### Changed

- Update is implemented for all resources. This means that if a resource already exists and is exactly the same as
  the one to be deployed, it will be updated instead of deleted and recreated.
- The `cdf-tk deploy` `--drop-data` is now independent of the `--drop` flag. This means that you can now drop data
  without dropping the resource itself. The reverse is not true, if you specify `--drop` without `--drop-data`, only
  resources that can be deleted without dropping data will be deleted.
- The output of the `cdf-tk deploy` command has been improved. Instead of created, deleted, and skipped resources
  being printed in a table at the end of the command, the resources are now printed as they are created, deleted, changed,
  and unchanged. In addition, an extra table is printed below with the datapoints that have been uploaded and dropped.
- The output of the `cdf-tk clean` command has also been changed in the same way as the `cdf-tk deploy` command.
- The `files` resource has been split into two resources, `FileMetadata` and `Files` to separate the metadata from
  the data (the file).
- To ensure comparison of resources and be able to determine whether they need to be updated, any resource
  defined in a YAML file will be augmented with default values (as defined by the CDF API) if they are missing before
  they are deployed.

### Fixed

- Bug in `auth` resource, this caused  groups with `all` and `resource` scoped capabilities to be written in two steps
  first with only `all` scoped capabilities and then all capabilities. This is now fixed by deploying groups in
  a single step.

## [0.1.0b5] - 2024-01-11

### Added

- Support for custom environment variables injected into build files when calling the command `cdf-tk deploy`.
- All resources that are unchanged are now skipped when running `cdf-tk deploy`.
- Support for loading `Group` Capabilities with scope `idScope` of type string. This means you can now set the
  `idScope` to the external id of a `dataSet` and it will be automatically replaced by the dataset id
  `cdf-tk deploy`.

### Fixed

- Fixed bug when calling any command loading a `.env` file and the path is not relative to the current working
  directory. This is now fixed.
- Calling `cdf-tk init --upgrade` overwrote all variables and comments set in the `config.yaml` file. This is now
  fixed.

### Improved

- Improved error message when missing a variable in `config.yaml` and a variable with the same name is defined
  for another module.

## [0.1.0b4] - 2024-01-08

### Added

- Added `--env-path` option to specify custom locations of `.env` file

### Fixed

- Fixed bug in command `cdf-tk build` that can occur when running on `Python>=3.10` which caused an error with text
  `TypeError: issubclass() arg 1 must be a class`. This is now fixed.

## [0.1.0b3] - 2024-01-02

### Fixed

- Fixed bug in `cdf-tk deploy` where auth groups with a mix of all and resource scoped capabilities skipped
  the all scoped capabilities. This is now fixed.

## [0.1.0b2] - 2023-12-17

### Fixed

- Handle duplicate `TransformationSchedules` when loading `Transformation` resources.
- Print table at the end of `cdf-tk deploy` failed with `AttributeError`, if any of resources were empty.
  This is now fixed.
- The `cdf-tk build` command no longer gives a warning about missing `sql` file for
  `TransformationSchedule`s.

## [0.1.0b1] - 2023-12-15

### Added

- Warnings if a configuration file is using `snake_case` when then resource type is expecting `camelCase`.
- Added support for validation of `space` for data models.
- Check for whether template variables `<change_me>` are present in the config files.
- Check for whether data set id is present in the config files.
- Print table at the end of `cdf-tk deploy` with the resources that were created, deleted, and skipped.
- Support for Extraction Pipelines and Extraction Pipeline configuration for remotely configured Extractors
- Separate loader for Transformation Schedule resources.

### Removed

- In the `deploy` command `drop_data` option has been removed. To drop data, use the `clean` command instead.

### Changed

- Require all spaces to be explicitly defined as separate .space.yaml file.
- The `data_set_id` for `Transformations` must now be set explicitly in the yaml config file for the `Transformation`
  under the `data_set_id` key. Note that you also need to explicitly define the `data_set` in its own yaml config file.
- All config files have been merged to a single config file, `config.yaml`. Upon calling `cdf-tk init` the `config.yaml`
  is created in the root folder of the project based on the `default.config.yaml` file of each module.
- DataSetID is no longer set implicitly when running the `cdf-tk deploy` command. Instead, the `data_set_id` must be
  set explicitly in the yaml config file.

### Fixed

- When running `cdf-tk deploy` with `--dry-run` a `ValueError` was raised if not all datasets were pre-existing.
  This is now fixed by skipping dataset validation when running with `--dry-run`.
- When having a `auth` group with mixed capabilities of all scoped and resource scoped, the all scoped capabilities
  were not removed when running `cdf-tk deploy`. This is now fixed.
- Loading `Transformation` did not support setting `dataSetExternalId` in the yaml config file. This is now fixed.

## [0.1.0a3] - 2023-12-01

### Changed

- Refactored load functionality. Loading raw tables and files now requires a `yaml` file with metadata.
- Fix container comparison to detect identical containers when loading data models (without --drop flag).
- Clean up error on resource does not exist when deleting (on `deploy --drop` or using clean command).

### Added

- Support for loading `data_sets`.
- Support for loading auth without --drop, i.e. `deploy --include=auth` and only changed groups are deployed.
- `cdf-tk --verbose build` now prints the resolution of modules and packages.
- Added `cdf-tk --version` to print the version of the tool and the templates.
- Support for `upsert` for `data_sets`.
- The cmd `cdf-tk deploy` creates the `data_set` before all other resources.
- Data sets are no longer implicitly created when referenced by another resource, instead an error is raised.
- Require all spaces to be explicitly defined as separate .space.yaml file.
- Add protection on group deletion and skip any groups that the current service principal belongs to.
- Support for multiple file resources per yaml config file for files resources.
- Support templated loading of * files in a folder when a single yaml has `externalId: something_$FILENAME`.
- You can now name the transformation .sql either with the externalId (as defined in the
  corresponding yaml file) or with the name of the file of the corresponding yaml file.
  I.e. if a transformation is defined in my_transformation.yaml with externalId:
  `tr_something`, the SQL file should be named either `tr_something.sql` or `my_transformation.sql`.
- Missing .sql files for transformations will now raise an error in the build step.
- The build step will now raise a number of warnings for missing externalIds in the yaml files,
  as well as if the naming conventions are not followed.
- System section in `environments.yaml` to track local state of `cdf-toolkit`.
- Introduced a `build_environment.yaml` in the `/build` folder to track how the build was run.

### Fixed

- `cdf-tk clean` not supporting `--include` properly.
- `cdf-tk clean` not working properly for data models with data.
- Fix group deletion on use of clean command to actually delete groups.

## [0.1.0a2] - 2023-11-22

### Fixed

- The `experimental` module was not included when running command `cdf-tk init`. This is now fixed.

## [0.1.0a1] - 2023-11-21

Initial release
