// Multi-Year Flood Progression Map (2019-2022-2025)
// LOAD DISTRICTS
var muzaffargarh = ee.FeatureCollection('projects/ee-msarfrazakhtar9944/assets/Muzaffrahgarh');
var multan = ee.FeatureCollection('projects/ee-msarfrazakhtar9944/assets/Multant');
var rajanpur = ee.FeatureCollection('projects/ee-msarfrazakhtar9944/assets/Rajanpur');
var dgkhan = ee.FeatureCollection('projects/ee-msarfrazakhtar9944/assets/DG_khan');
// Merge all districts
var roi = muzaffargarh.merge(multan).merge(rajanpur).merge(dgkhan);
Map.centerObject(roi, 9);
Map.addLayer(roi, {color: 'black', fillColor: '00000000'}, 'District Boundaries');
// 2. CLOUD MASK FUNCTION (Sentinel-2 SR)
function maskS2Clouds(image) {
var qa = image.select('QA60');
var cloudBitMask = 1 << 10;
var cirrusBitMask = 1 << 11;
var mask = qa.bitwiseAnd(cloudBitMask).eq(0)
.and(qa.bitwiseAnd(cirrusBitMask).eq(0));
return image.updateMask(mask)
.divide(10000)
.copyProperties(image, ['system:time_start']);
}
// 3. DEFINE PERMANENT WATER (PRE-FLOOD 2025 BASELINE)
var beforeCol = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
.filterBounds(roi)
.filterDate('2025-01-01', '2025-02-28')
.filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
.map(maskS2Clouds);
var beforeImg = beforeCol.median();
var mndwiBefore = beforeImg.normalizedDifference(['B3', 'B11']).rename('MNDWI_Before');
var permanentWater = mndwiBefore.gt(0); // This is now defined before use
// 4. HELPER FUNCTION FOR YEARLY FLOODS
// Assigns a unique integer to each year to create a single categorical layer
function getFloodYear(startDate, endDate, permWater, yearValue) {
var col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
.filterBounds(roi)
.filterDate(startDate, endDate)
.filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
.map(maskS2Clouds);
var floodImg = col.median();
var mndwi = floodImg.normalizedDifference(['B3', 'B11']);
var floodWater = mndwi.gt(0);
// Keep only water that IS NOT permanent water, then multiply by yearValue
return floodWater.where(permWater, 0).selfMask().multiply(yearValue).toByte();
}
// 5. CALCULATE FLOOD LAYERS
// Values: 2=2019, 3=2022, 4=2025
var flood2019 = getFloodYear('2019-07-01', '2019-09-30', permanentWater, 2);
var flood2022 = getFloodYear('2022-07-01', '2022-09-30', permanentWater, 3);
var flood2025 = getFloodYear('2025-07-01', '2025-09-30', permanentWater, 4);
// 6. COMBINE INTO SINGLE LAYER
// Starts with Permanent Water (Value 1) and overlays newer years on top
var multiYearFlood = ee.Image(1).updateMask(permanentWater)
.blend(flood2019)
.blend(flood2022)
.blend(flood2025)
.clip(roi);
// 7. VISUALIZATION & MAPPING
var multiPalette = [
'#08306b', // 1: Permanent Water (Dark Blue)
'#9ecae1', // 2: 2019 Flood (Light Blue)
'#4292c6', // 3: 2022 Flood (Medium Blue)
'#ef3b2c' // 4: 2025 Flood (Red)
];
Map.addLayer(multiYearFlood, {min: 1, max: 4, palette: multiPalette}, 'Flood Progression (2019-2025)');
// 8. TITLE & LEGEND UI
var title = ui.Panel({
style: {position: 'top-center', padding: '8px'}
});
title.add(ui.Label({
value: 'Multi-Year Flood Progression Map',
style: {fontSize: '18px', fontWeight: 'bold'}
}));
Map.add(title);
var legend = ui.Panel({
style: {position: 'bottom-left', padding: '10px'}
});
function legendItem(color, label) {
return ui.Panel([
ui.Label({style: {backgroundColor: color, padding: '8px', border: '1px solid black'}}),
ui.Label({value: label, style: {margin: '0 0 0 6px'}})
], ui.Panel.Layout.Flow('horizontal'));
}
legend.add(ui.Label('Legend', {fontWeight: 'bold'}));
legend.add(legendItem('#1F4E79', 'Permanent Water'));
legend.add(legendItem('#FFE699', 'Flood 2019 Only'));
legend.add(legendItem('#F4A300', 'Flood 2022 Only'));
legend.add(legendItem('#C00000', 'Flood 2025 Only'));
Map.add(legend);
// 9. EXPORT COMBINED LAYER
Export.image.toDrive({
image: multiYearFlood,
description: 'Muzaffargarh_MultiYear_Flood_2019_2025',
folder: 'GEE_Exports',
region: roi,
scale: 10,
maxPixels: 1e13
});
