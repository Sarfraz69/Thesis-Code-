// Random Forest LULC Classification (2019, 2022, 2025) — Google Earth Engine
// ===========================
// 1. Study Area
// ===========================
var studyArea = table.merge(table2);
Map.centerObject(studyArea, 9);
Map.addLayer(studyArea, {color:'red', fillColor:'00000000'}, 'Study Area');
// ===========================
// 2. Sentinel-2 composite + indices
// ===========================
function getComposite(year, cloudMax) {
var col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
.filterBounds(studyArea)
.filterDate(year+'-01-01', year+'-12-31')
.filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloudMax))
.select(['B2','B3','B4','B5','B6','B7','B8','B8A','B11','B12']);
var median = col.median().clip(studyArea);
var ndvi = median.normalizedDifference(['B8','B4']).rename('NDVI');
var ndwi = median.normalizedDifference(['B3','B8']).rename('NDWI');
var ndbi = median.normalizedDifference(['B11','B8']).rename('NDBI');
return median.addBands([ndvi, ndwi, ndbi]);
}
// ===========================
// 3. Composites
// ===========================
var comp2019 = getComposite('2019', 20);
var comp2022 = getComposite('2022', 20);
var comp2025 = getComposite('2025', 30);
// ===========================
// 4. Prepare training points
// ===========================
function prepareTraining(collection, classValue) {
return collection.map(function(f){
return f.set('Class', classValue);
});
}
var trainingPointsNumeric = prepareTraining(Barren, 1)
.merge(prepareTraining(Vegetation, 2))
.merge(prepareTraining(Water, 3))
.merge(prepareTraining(Builtup, 4));
Map.addLayer(trainingPointsNumeric, {color:'black'}, 'Training Points');
// ===========================
// 5. Bands
// ===========================
var bands = ['B2','B3','B4','B5','B6','B7','B8','B8A','B11','B12','NDVI','NDWI','NDBI'];
// ===========================
// 6. Color palette
// ===========================
var classPalette = ['#d3d3d3', '#00ff00', '#0000ff', '#ff0000']; // Barren, Vegetation, Water, Built-up

// ===========================
// 7. Classification function
// ===========================
function classifyYear(image, year) {
// Sample image at training points
var samples = image.sampleRegions({
collection: trainingPointsNumeric,
properties: ['Class'],
scale: 10,
geometries: true
});
// Split into train (70%) / test (30%)
var split = samples.randomColumn('random');
var train = split.filter(ee.Filter.lt('random', 0.7));
var test = split.filter(ee.Filter.gte('random', 0.7));
// Train Random Forest
var classifier = ee.Classifier.smileRandomForest(100).train({
features: train,
classProperty: 'Class',
inputProperties: bands
});
// Classify image
var classified = image.select(bands).classify(classifier);
// Accuracy assessment
var testPred = test.classify(classifier);
var errorMatrix = testPred.errorMatrix('Class', 'classification');
print('--- Accuracy report ' + year + ' ---');
print('Error Matrix:', errorMatrix);
print('Overall Accuracy:', errorMatrix.accuracy());
print('Kappa:', errorMatrix.kappa());
// Display classified image
Map.addLayer(classified,
{min:1, max:4, palette:classPalette},
'LULC ' + year
);
// Return classified image for export
return classified;
}
// ===========================
// 8. Classify all years
// ===========================
var classified2019 = classifyYear(comp2019, '2019');
var classified2022 = classifyYear(comp2022, '2022');
var classified2025 = classifyYear(comp2025, '2025');
// ===========================
// 9. Export each year to Drive
// ===========================
var exports = [
{img: classified2019, year: '2019'},
{img: classified2022, year: '2022'},
{img: classified2025, year: '2025'}
];
exports.forEach(function(e){
Export.image.toDrive({
image: e.img,
description: 'LULC_' + e.year,
folder: 'LULC_Maps',
fileNamePrefix: 'LULC_' + e.year,
region: studyArea,
scale: 10,
maxPixels: 1e13
});
});
// ===========================
// 10. Add legend
// ===========================
var legend = ui.Panel({style: {position: 'bottom-left', padding: '8px 15px'}});
legend.add(ui.Label('LULC Classes'));
var classNames = ['Barren','Vegetation','Water','Built-up'];
for (var i = 0; i < classNames.length; i++) {
var colorBox = ui.Label('', {backgroundColor: classPalette[i], padding: '8px', margin: '2px 0'});
var nameLabel = ui.Label(classNames[i], {margin: '2px 0 2px 6px'});
legend.add(ui.Panel([colorBox, nameLabel], ui.Panel.Layout.Flow('horizontal')));
}
Map.add(legend);
