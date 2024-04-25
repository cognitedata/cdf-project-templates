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

## [TBD]

### Changed

- The `cdf_functions_dummy` module now includes codes from the former `common_function_code` directory.

## [0.2.0a3] - 2024-04-23

### Fixed

- Align tag name in asset hierarchy between the 2 example transformations
- Added default root asset ID to documents for initial annotation
- Aligned use of asset external ID across contextualization functions
- Annotation logic with local time stamp for when to reprocess P&ID files
- Input to P&ID annotation based on list of synonyms for tag
- Updated module `apm_simple_data_model` for `cognite-sdk>=7.37`, i.e., container properties
  of type `direct` have now `list: false` explicitly set.

### Added

- Added Transformation for WorkOrder and WorkItems to OID testdata template
- Added Workflow with a Function and a Transformation to the custom module example
- Added annotationsAcl, eventsAcl and labelsAcl to admin groups


## [0.2.0a2] - 2024-04-03

No changes to templates.

## [0.2.0a1] - 2024-03-20

- Added functionality for wildcard detection of tags in P&ID
- Added functionality for multiple overlapping annotation to same tag - related to wildcards

## [0.1.2] - 2024-03-18

No changes to templates.

## [0.1.1] - 2024-03-11

No changes to templates.

### Added

- Module `cognite_modules/example/cdf_data_pipeline_timeseries_valhall` opcua / time series
  extractor pipeline, CDF function running contextualization of time series to assets.

## [0.1.0] - 2024-02-29

### Changed

- In the `infield` section, the `infield_apm_app_config.node.yaml` was moved from `cdf_infield_location` to `cdf_infield_common`
  module. In addition, the module `cdf_infield_second_location` was added to the `infield` section. This is to demonstrate
  how multiple locations in Infield should be handled.
- In the `cdf_data_pipeline_files_valhall` example, the Cognite Function `fu_context_files_oid_fileshare_annotation`
  has been renamed to `fn_context_files_oid_fileshare_annotation`. It has also been split into several files, to be
  easier to understand. It has also been changed to using `print`s (over `logging`), as that is unfortunately a hard
  requirement from the API.

### Added

- In the `cdf_data_pipeline_files_valhall` example, the `README.md` file has been updated with instructions on how to
  run and test Cognite Functions locally.

## [0.1.0b9] - 2024-02-20

### Changed

- In cdf_oid_example_data, the filename prefixes have been removed from the filenames and instead the new name template
  functionality is used to prefix the filenames as part of the build step.

### Fixed

- Replaced `shared: True` to `isPublic: True` and `action: upsert` to `conflictMode: upsert` in all
  transformation configurations to match the CDF API specification.

## [0.1.0b8] - 2024-02-14

### Added

- Added a new module `cognite_modules/example/cdf_data_pipeline_files_valhall` file extractor pipeline, transformation
  and CDF function running annotation on P&ID documents.

### Fixed

- Added missing cognite-sdk dependency to the common_functions_code.

## [0.1.0b7] - 2024-02-07

- Added a new module `cognite_modules/example/cdf_functions_dummy` that shows how to create functions and deploy them.
- Added common function code examples in `common_function_code/` directory as well as an
  example of how to use the common code in the `cognite_modules/example/cdf_functions_dummy/fn_test2` and
  `fn_example_repeater` functions.

### Fixed

- In module `cognite_modules/example/example_pump_asset_hierarchy`, in the transformation
  `pump_asset_hierarchy_load-collections_pump.sql` the value `pump_assets` was hardcoded instead of using the variable
  `{{raw_db}}`. This has been fixed.

## [0.1.0b6] - 2024-01-26

No changes to templates.

## [0.1.0b5] - 2024-01-11

No changes to templates.

## [0.1.0b4] - 2024-01-08

No changes to templates.

## [0.1.0b3] - 2024-01-02

No changes to templates.

## [0.1.0b2] - 2023-12-17

### Fixed

- In the package `example_pump` ensure all transformations are prefixed with `tr_`.

## [0.1.0b1] - 2023-12-15

### Added

- Explicitly define model `space` in `experimental/cdf_asset_source_model/` and `experimental/example_pump_model/`.
- The module `my_example_module` has been added to the `custom_modules` folder.
- Added globally defined schedule variables that can be used across all modules.
- A complete example of an Asset data pipeline in `examples/cdf_asset_data_pipeline/` shows how to configure an
  Extractor, monitor the status of the Extraction Pipeline, and load the data into the asset hierarchy using Transformations.
- DataSet to all example modules: `cdf_apm_simple_data_model`, `cdf_asset_source_model`, `cdf_oid_example_data`,
  `example_pump_data_model`, `example_pump_asset_hierarchy`.

### Changed

- **BREAKING** All externalIds and names have been changed to follow the naming conventions for resources
  in `examples/cdf_oid_example_data`, `examples/cdf_apm_simple_data_model`, `modules/cdf_apm_base`,
  `modules/cdf_infield_common`, and `modules/cdf_infield_location`.
- **BREAKING** Transformation Schedules broken out into separate files, following naming convention `<transformation_name>.schedule.yaml`.
- All cognite templates have been moved into `cognite_templates` folder, while `local_templates` is renamed to `custom_templates`.
- Move cdf_apm_base into separate folder.
- The file `local.yaml` has been renamed `environments.yaml` to better reflect its purpose.
- Removed demo `sourceId` from `cdf_infield_location` module.
- Changed the isPaused flag to use a module-level variable instead of hardcoded in `cdf_apm_simple_data_model`.
- Combined the child and parent transformations `sync_assets_from_hierarchy_to_apm` in `cdf_infield_location`.
  This has the benefit of not having to wait for the parent transformation to finish before starting the child transformation,
  thus no longer a dependency between the two transformations.

### Fixed

- Removed transformation identity provider variables from modules and reused the global cicd_ prefixed ones.
- Ensure all transformations in `cognite_modules` are prefixed with `tr_` and all spaces are prefixed with `sp_`.

## [0.1.0a3] - 2023-11-29

### Changed

- Remove unused template_version variable from groups and use of group metadata.
- Split up cdf_oid_example_data into data sets and RAW databases per source system.

### Fixed

- Add space yaml files for existing data models when explicit space definition was introduced.
- Fix use of integer value in version for data models.
- Fix wrong reference to `apm_simple` in `examples/cdf_apm_simple_data_model` and `modules/cdf_infield_location`.
- Exemplify use of a single config yaml file for multiple file resources in `examples/cdf_oid_example_data/files/files.yaml`.

## [0.1.0a2] - 2023-11-23

### Changed

- Changed format of infield external_ids to be more readable, moving `_dataset` (ds) and `_space` to the beginning of
  the external_id.
- `examples/cdf_apm_simple/raw` and `examples/example_dump_asst_hierarchy/raw` now explicitly
  defines database and table name in `.yaml` files for each table.
- Added `data_set` to `examples/example_dump_asst_hierarchy/`, which was implicitly defined in
  before.

### Fixed

- cdf_infield_common module and the auth applications-configuration.yaml did not load group source id
   correctly due to source_id being used instead of sourceId. This is now fixed.

## [0.1.0a1] - 2023-11-21

Initial release
