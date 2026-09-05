// Danger Zone / Risk Zone — River flood risk buffers (Rajanpur)
// ===============================
// LOAD DISTRICT
// ===============================
var district = ee.FeatureCollection(
'projects/ee-msarfrazakhtar9944/assets/Rajanpur'
);
Map.centerObject(district, 9);
Map.addLayer(district, {color: 'black'}, 'Rajanpur');
// ===============================
// LOAD RIVERS
// ===============================
var river = ee.FeatureCollection(
'projects/ee-msarfrazakhtar9944/assets/pakistan-waterways-shape'
);
// ===============================
// CREATE MULTI DISTANCE BUFFERS (meters)
// ===============================
var bufferDistances = [1000, 3000, 5000, 7000, 10000]; // in meters
var buffers = bufferDistances.map(function(dist){
return river.map(function(f){
return f.buffer(dist);
}).geometry().intersection(district.geometry());
});
// ===============================
// RISK RASTER
// ===============================
var base = ee.Image(0).clip(district);
var risk = base
.where(ee.Image().paint(buffers[4], 1), 1) // Very Low
.where(ee.Image().paint(buffers[3], 2), 2) // Low
.where(ee.Image().paint(buffers[2], 3), 3) // Moderate
.where(ee.Image().paint(buffers[1], 4), 4) // High
.where(ee.Image().paint(buffers[0], 5), 5); // Very High
// ===============================
// DISPLAY RISK ZONES
// ===============================
var palette = [
'#313695', // Very Low (Oxford Atlas style)
'#74add1', // Low
'#fee08b', // Moderate
'#f46d43', // High
'#a50026' // Very High
];
Map.addLayer(risk, {min: 1, max: 5, palette: palette}, 'River Risk Zones');
// ===============================
// ADD LEGEND
// ===============================
var legend = ui.Panel({style: {position: 'bottom-right', padding: '8px 15px'}});
// Legend title
var legendTitle = ui.Label({
value: 'River Flood Risk Zones',
style: {fontWeight: 'bold', fontSize: '14px', margin: '0 0 6px 0', padding: '0'}
});
legend.add(legendTitle);
// Risk labels and colors
var riskLevels = ['Very Low', 'Low', 'Moderate', 'High', 'Very High'];
for (var i = 0; i < riskLevels.length; i++) {
var colorBox = ui.Label({
style: {
backgroundColor: palette[i],
padding: '8px',
margin: '0 0 4px 0'
}
});
var description = ui.Label({
value: riskLevels[i],
style: {margin: '0 0 4px 6px'}
});
var legendItem = ui.Panel({
widgets: [colorBox, description],
layout: ui.Panel.Layout.Flow('horizontal')
});
legend.add(legendItem);
}
Map.add(legend);
Export.image.toDrive({
image: risk,
description: 'Muzaffargarh_River_Risk_Zones',
folder: 'GEE_Exports', // Change folder name if you want
fileNamePrefix: 'Muzaffargarh_Risk',
region: district.geometry(), // Clip to district boundary
scale: 30, // Set pixel resolution (meters)
crs: 'EPSG:4326', // WGS84, change if needed
maxPixels: 1e13
});
