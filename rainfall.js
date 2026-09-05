// Rainfall Total (June-September) — Rajanpur/Muzaffargarh
// Load your Muzaffargarh region
var muzaffargarh = ee.FeatureCollection("projects/ee-msarfrazakhtar9944/assets/Rajanpur");
// Calculate total rainfall June-September 2025
var totalRainfall = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
.filterDate('2019-06-01', '2019-09-30')
.filterBounds(muzaffargarh)
.select('precipitation')
.sum()
.clip(muzaffargarh);
// Preview on map
Map.centerObject(muzaffargarh, 9);
Map.addLayer(muzaffargarh, {color: 'red'}, 'Muzaffargarh');
Map.addLayer(totalRainfall, {min: 0, max: 400, palette: ['white', 'blue', 'darkblue']}, 'Rainfall');
// EXPORT 1: Main rainfall raster
Export.image.toDrive({
image: totalRainfall,
description: 'Rajanpur_Rainfall_2019',
scale: 1000,
region: muzaffargarh.geometry(),
maxPixels: 1e9,
folder: 'GEE_Exports',
fileNamePrefix: 'rainfall_Rajanpur_2019',
crs: 'EPSG:4326',
fileFormat: 'GeoTIFF'
});
// EXPORT 2: District boundary
Export.table.toDrive({
collection: muzaffargarh,
description: 'Muzaffargarh_Boundary',
folder: 'GEE_Exports',
fileNamePrefix: 'muzaffargarh_boundary',
fileFormat: 'SHP'
});
print(' Ready to export! Check Tasks tab.');
print('1. Total Rainfall Raster will be exported as GeoTIFF');
print('2. District Boundary will be exported as Shapefile');
