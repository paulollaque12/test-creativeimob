-- Limites de municipios (admin_level 8) e bairros (admin_level 10) da Grande Florianopolis, do OpenStreetMap (ODbL),
-- dataset publico do BigQuery (location US). Rodar no conector e salvar o resultado em /tmp/osm_rows.json
-- (campos: id, name, al, gj, clat, clon); depois: python tools/build_geo.py  -> /tmp/pdgeo.json (cole em `const PDG=` do HTML).
WITH f AS (SELECT osm_id, (SELECT value FROM UNNEST(all_tags) WHERE key='name') name, (SELECT value FROM UNNEST(all_tags) WHERE key='admin_level') al, geometry g
 FROM `bigquery-public-data.geo_openstreetmap.planet_features`
 WHERE feature_type='multipolygons' AND EXISTS(SELECT 1 FROM UNNEST(all_tags) WHERE key='boundary' AND value='administrative')
 AND (SELECT value FROM UNNEST(all_tags) WHERE key='admin_level') IN ('8','10')
 AND ST_INTERSECTS(geometry, ST_GEOGFROMTEXT('POLYGON((-48.95 -28.0,-48.3 -28.0,-48.3 -27.3,-48.95 -27.3,-48.95 -28.0))')))
SELECT osm_id, name, al, ST_ASGEOJSON(ST_SIMPLIFY(g, IF(al='8',120,45))) gj, ST_Y(ST_CENTROID(g)) clat, ST_X(ST_CENTROID(g)) clon
FROM f WHERE name IS NOT NULL AND ST_Y(ST_CENTROID(g)) BETWEEN -28.0 AND -27.3 AND ST_X(ST_CENTROID(g)) BETWEEN -48.95 AND -48.3;
