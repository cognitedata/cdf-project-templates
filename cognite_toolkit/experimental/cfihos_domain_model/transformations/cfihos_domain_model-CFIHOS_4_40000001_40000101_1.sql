SELECT 
  cast(`source_property` as Float) as CFIHOS_40000001,
  cast(`source_property` as String) as CFIHOS_40000001_UOM,
  cast(`source_property` as String) as CFIHOS_40000009,
  cast(`source_property` as String) as CFIHOS_40000010,
  cast(`source_property` as String) as CFIHOS_40000011,
  cast(`source_property` as String) as CFIHOS_40000033,
  cast(`source_property` as Boolean) as CFIHOS_40000039,
  cast(`source_property` as Float) as CFIHOS_40000060,
  cast(`source_property` as Boolean) as CFIHOS_40000070,
  cast(replace(`cfihosTagID`,'-','_') as String) as entityType,
  cast(`source_property` as String) as externalId
FROM `source_database`.`source_table`
WHERE isnotnull(`cfihosTagID`) AND isnotnull(`source_property`)