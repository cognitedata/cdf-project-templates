SELECT 
  cast(`source_property` as String) as CFIHOS_10000128,
  if(isnotnull(key), node_reference('cfihos_domain_model', cast(`key` as String)), null) as CFIHOS_10000128_rel,
  cast(`source_property` as String) as CFIHOS_10000153,
  cast(`source_property` as String) as CFIHOS_10000157,
  if(isnotnull(key), node_reference('cfihos_domain_model', cast(`key` as String)), null) as CFIHOS_10000157_rel,
  cast(`source_property` as String) as CFIHOS_10000158,
  if(isnotnull(key), node_reference('cfihos_domain_model', cast(`key` as String)), null) as CFIHOS_10000158_rel,
  cast(`source_property` as String) as CFIHOS_10000159,
  if(isnotnull(key), node_reference('cfihos_domain_model', cast(`key` as String)), null) as CFIHOS_10000159_rel,
  cast(`source_property` as String) as CFIHOS_10000163,
  cast(`source_property` as String) as CFIHOS_10000166,
  if(isnotnull(key), node_reference('cfihos_domain_model', cast(`key` as String)), null) as CFIHOS_10000166_rel,
  cast(`source_property` as String) as CFIHOS_10000177,
  cast(`source_property` as String) as CFIHOS_10000178,
  if(isnotnull(key), node_reference('cfihos_domain_model', cast(`key` as String)), null) as CFIHOS_10000178_rel,
  cast(`source_property` as String) as CFIHOS_10000179,
  if(isnotnull(key), node_reference('cfihos_domain_model', cast(`key` as String)), null) as CFIHOS_10000179_rel,
  cast(`source_property` as String) as CFIHOS_10000182,
  if(isnotnull(key), node_reference('cfihos_domain_model', cast(`key` as String)), null) as CFIHOS_10000182_rel,
  cast(replace(`cfihosTagID`,'-','_') as String) as entityType,
  cast(`source_property` as String) as externalId
FROM `source_database`.`source_table`
WHERE isnotnull(`cfihosTagID`) AND isnotnull(`source_property`)