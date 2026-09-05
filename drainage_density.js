// Drainage Density — Rajanpur District (MERIT Hydro)
// Load AOI
var AOI = ee.FeatureCollection("projects/ee-msarfrazakhtar9944/assets/Rajanpur");
// Load MERIT Hydro
var hydro = ee.Image('MERIT/Hydro/v1_0_1');
var upa = hydro.select('upa');
// Define streams
var threshold_km2 = 0.1; // lower to ensure raster visibility
var streams = upa.gt(threshold_km2).updateMask(upa.gt(threshold_km2));
// Convert streams raster to vector polygons
var streamsVector = streams.reduceToVectors({
geometry: AOI,
scale: 90,
geometryType: 'polygon',
eightConnected: true
});
// Add a numeric property to each feature for rasterization
streamsVector = streamsVector.map(function(f){
return f.set('value', 1);
});
// Convert vector back to raster
var streamRasterFromVector = streamsVector.reduceToImage({
properties: ['value'], // numeric property to rasterize
reducer: ee.Reducer.first() // take first (value = 1)
});
// Compute drainage density per pixel (km/km²)
var pixelSize_km = 0.09;
var pixelArea_km2 = pixelSize_km * pixelSize_km;
var drainageDensityRaster =
streamRasterFromVector.multiply(pixelSize_km).divide(pixelArea_km2);
// Smooth raster with 3×3 kernel
var kernel = ee.Kernel.square({radius: 1, units: 'pixels', normalize: true});
drainageDensityRaster = drainageDensityRaster.convolve(kernel);
// Clip to AOI
drainageDensityRaster = drainageDensityRaster.clip(AOI);
// Visualization
var visParams = {min:0, max:20, palette:['white','lightblue','blue','darkblue']};
Map.centerObject(AOI, 10);
Map.addLayer(drainageDensityRaster, visParams, 'Smoothed Drainage Density');
Map.addLayer(AOI, {}, 'AOI boundary');
// Export raster as GeoTIFF
Export.image.toDrive({
image: drainageDensityRaster,
description: 'Muzaffrahgarh_DrainageDensity_Smooth',
scale: 90,
region: AOI,
fileFormat: 'GeoTIFF',
maxPixels: 1e13
});
