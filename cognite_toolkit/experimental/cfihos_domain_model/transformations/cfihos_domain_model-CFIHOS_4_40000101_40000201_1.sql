SELECT 
  cast(`source_property` as String) as CFIHOS_40000108,
  cast(`source_property` as String) as CFIHOS_40000109,
  cast(`source_property` as String) as CFIHOS_40000110,
  cast(`source_property` as String) as CFIHOS_40000111,
  cast(`source_property` as String) as CFIHOS_40000112,
  cast(`source_property` as String) as CFIHOS_40000123,
  cast(`source_property` as Boolean) as CFIHOS_40000158,
  cast(`source_property` as String) as CFIHOS_40000173,
  cast(`source_property` as String) as CFIHOS_40000174,
  cast(`source_property` as String) as CFIHOS_40000178,
  cast(replace(`cfihosTagID`,'-','_') as String) as entityType,
  cast(`source_property` as String) as externalId
FROM `source_database`.`source_table`
WHERE isnotnull(`cfihosTagID`) AND isnotnull(`source_property`)