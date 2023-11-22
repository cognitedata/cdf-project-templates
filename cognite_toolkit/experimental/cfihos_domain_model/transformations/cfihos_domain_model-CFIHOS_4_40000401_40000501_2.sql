SELECT 
  cast(`source_property` as Float) as CFIHOS_40000485,
  cast(`source_property` as String) as CFIHOS_40000488,
  cast(`source_property` as Float) as CFIHOS_40000489,
  cast(`source_property` as String) as CFIHOS_40000489_UOM,
  cast(`source_property` as Float) as CFIHOS_40000491,
  cast(`source_property` as Float) as CFIHOS_40000494,
  cast(`source_property` as String) as CFIHOS_40000494_UOM,
  cast(`source_property` as Float) as CFIHOS_40000496,
  cast(`source_property` as String) as CFIHOS_40000496_UOM,
  cast(`source_property` as Float) as CFIHOS_40000499,
  cast(`source_property` as String) as CFIHOS_40000499_UOM,
  cast(`source_property` as Float) as CFIHOS_40000500,
  cast(`source_property` as String) as CFIHOS_40000500_UOM,
  cast(replace(`cfihosTagID`,'-','_') as String) as entityType,
  cast(`source_property` as String) as externalId
FROM `source_database`.`source_table`
WHERE isnotnull(`cfihosTagID`) AND isnotnull(`source_property`)