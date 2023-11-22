SELECT 
  cast(`source_property` as Float) as CFIHOS_40000201,
  cast(`source_property` as String) as CFIHOS_40000201_UOM,
  cast(`source_property` as Float) as CFIHOS_40000211,
  cast(`source_property` as String) as CFIHOS_40000211_UOM,
  cast(`source_property` as String) as CFIHOS_40000250,
  cast(`source_property` as Float) as CFIHOS_40000259,
  cast(`source_property` as Float) as CFIHOS_40000260,
  cast(`source_property` as Float) as CFIHOS_40000273,
  cast(`source_property` as Float) as CFIHOS_40000274,
  cast(`source_property` as Float) as CFIHOS_40000275,
  cast(`source_property` as String) as CFIHOS_40000275_UOM,
  cast(replace(`cfihosTagID`,'-','_') as String) as entityType,
  cast(`source_property` as String) as externalId
FROM `source_database`.`source_table`
WHERE isnotnull(`cfihosTagID`) AND isnotnull(`source_property`)