SELECT 
  cast(`source_property` as String) as CFIHOS_40000615,
  cast(replace(`cfihosTagID`,'-','_') as String) as entityType,
  cast(`source_property` as String) as externalId
FROM `source_database`.`source_table`
WHERE isnotnull(`cfihosTagID`) AND isnotnull(`source_property`)