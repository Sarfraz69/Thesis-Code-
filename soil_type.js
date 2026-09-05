// Soil Clay Content Map — Rajanpur District (SoilGrids)
// SOIL CLAY MAP FOR RAJANPUR DISTRICT
var rajanpur = ee.FeatureCollection("projects/ee-msarfrazakhtar9944/assets/Rajanpur");
// Get soil clay data (0-30cm average)
var soilClay = ee.Image("projects/soilgrids-isric/clay_mean")
.select(['clay_0-5cm_mean', 'clay_5-15cm_mean', 'clay_15-30cm_mean'])
.reduce(ee.Reducer.mean())
.clip(rajanpur)
.rename('clay_percentage');
// Add to map for preview
Map.centerObject(rajanpur, 9);
Map.addLayer(rajanpur, {color: 'red', fillColor: '00000000'}, 'Rajanpur District');
Map.addLayer(soilClay, {
min: 10,
max: 60,
palette: ['#ffffcc', '#c7e9b4', '#7fcdbb', '#41b6c4', '#2c7fb8', '#253494', '#081d58']
}, 'Soil Clay Content (%)');
// Export for ArcGIS
Export.image.toDrive({
image: soilClay,
description: 'Rajanpur_Soil_Clay_Map',
scale: 250,
region: rajanpur.geometry(),
maxPixels: 1e9,
folder: 'GEE_Exports',
fileNamePrefix: 'rajanpur_soil_clay',
crs: 'EPSG:4326',
fileFormat: 'GeoTIFF'
});
print(' Rajanpur soil clay map ready for export! Check Tasks tab.');
