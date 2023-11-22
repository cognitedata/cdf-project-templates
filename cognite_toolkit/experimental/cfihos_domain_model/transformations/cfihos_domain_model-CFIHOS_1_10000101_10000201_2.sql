SELECT 
  cast(`source_property` as String) as CFIHOS_10000184,
  if(isnotnull(key), node_reference('cfihos_domain_model', cast(`key` as String)), null) as CFIHOS_10000184_rel,
  cast(replace(`cfihosTagID`,'-','_') as String) as entityType,
  cast(`source_property` as String) as externalId
FROM `source_database`.`source_table`
WHERE isnotnull(`cfihosTagID`) AND isnotnull(`source_property`)