--
-- Update file metdata using Transformation
--
-- Input data from RAW DB table (using example data) and uploaded files
--
With 
  root_id AS (
     Select id from _cdf.asset where externalId = '{{external_root_id_asset}}'
  )
SELECT
  file.id                          as id,
  file.name                        as name,
  '{{location_name}}_'|| file.name as  externalId,
  meta.source                      as source,
  meta.`mime_type`                 as mimeType,
  array(root_id.id)                as assetIds,
  dataset_id('{{files_dataset}}')  as dataSetId,
  to_metadata(doc_type)            as metadata
FROM 
  `{{files_raw_input_db}}`.`{{files_raw_input_table}}` meta,
  _cdf.files                             file,
  root_id
WHERE 
  file.name = meta.name
