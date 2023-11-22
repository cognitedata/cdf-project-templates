SELECT 
  cast(`source_property` as String) as CFIHOS_10000001,
  if(isnotnull(key), node_reference('cfihos_domain_model', cast(`key` as String)), null) as CFIHOS_10000001_rel,
  cast(`source_property` as String) as CFIHOS_10000005,
  if(isnotnull(key), node_reference('cfihos_domain_model', cast(`key` as String)), null) as CFIHOS_10000005_rel,
  cast(`source_property` as Boolean) as CFIHOS_10000028,
  cast(`source_property` as Boolean) as CFIHOS_10000036,
  cast(`source_property` as String) as CFIHOS_10000040,
  if(isnotnull(key), node_reference('cfihos_domain_model', cast(`key` as String)), null) as CFIHOS_10000040_rel,
  cast(CASE WHEN `Facility` = 'A' THEN 'Munin' WHEN `Facility` = 'C' THEN 'Sentral Template' WHEN `Facility` = 'D' THEN 'Hugin A' WHEN `Facility` = 'E' THEN 'Rind' WHEN `Facility` = 'F' THEN 'Fulla & Lillefrigg' WHEN `Facility` = 'G' THEN 'Hugin B NUI' WHEN `Facility` = 'N' THEN 'Langfjellet North' WHEN `Facility` = 'S' THEN 'Langfjellet South' WHEN `Facility` = 'P' THEN 'Børdalen Transformer station' WHEN `Facility` = 'Q' THEN 'Årskog compensation station' WHEN `Facility` = 'O' THEN 'Integrated Operations centre Centre' WHEN `Facility` = 'U' THEN 'Export lines' WHEN `Facility` = 'V' THEN 'Askja A template' WHEN `Facility` = 'W' THEN 'Askja B template' WHEN `Facility` = 'X' THEN 'Electrical transmission lines' WHEN `Facility` = 'Y' THEN 'Krafla B Template' WHEN `Facility` = 'Z' THEN 'Krafla A Template' END as String) as CFIHOS_10000084,
  if(isnotnull(key), node_reference('cfihos_domain_model', cast(`key` as String)), null) as CFIHOS_10000084_rel,
  cast(replace(`cfihosTagID`,'-','_') as String) as entityType,
  cast(`source_property` as String) as externalId
FROM `source_database`.`source_table`
WHERE isnotnull(`cfihosTagID`) AND isnotnull(`source_property`)