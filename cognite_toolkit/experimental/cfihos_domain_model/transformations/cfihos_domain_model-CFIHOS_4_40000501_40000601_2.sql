SELECT 
  cast(`source_property` as String) as CFIHOS_40000579,
  cast(`source_property` as Float) as CFIHOS_40000581,
  cast(`source_property` as Float) as CFIHOS_40000582,
  cast(`source_property` as Float) as CFIHOS_40000583,
  cast(`source_property` as Boolean) as CFIHOS_40000585,
  cast(`source_property` as String) as CFIHOS_40000599,
  cast(`source_property` as String) as CFIHOS_40000600,
  cast(replace(`cfihosTagID`,'-','_') as String) as entityType,
  cast(`source_property` as String) as externalId
FROM `source_database`.`source_table`
WHERE isnotnull(`cfihosTagID`) AND isnotnull(`source_property`)