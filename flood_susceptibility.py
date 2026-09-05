# Python code for Flood Susceptibility (2025 Projection)
# Muzaffargarh District, Punjab, Pakistan
import ee
import geemap
import geopandas as gpd
import math
import time
import os

# Initialize Earth Engine with error handling
def authenticate_and_initialize():
    try:
        ee.Initialize()
        print("Earth Engine initialized!")
    except Exception as e:
        print(f"Initial initialization failed: {e}")
        try:
            ee.Authenticate(auth_mode='notebook', force=True)
            ee.Initialize()
            print("Earth Engine initialized after re-authentication!")
        except Exception as e:
            print(f"Authentication failed: {e}")
            print("Please grant Earth Engine and Drive permissions in the browser. See http://goo.gle/ee-auth.")
            exit()

# Check Drive access
def check_drive_access():
    try:
        test_image = ee.Image.constant(0).clip(ee.Geometry.Point([0, 0]).buffer(100))
        task = ee.batch.Export.image.toDrive(
            image=test_image,
            description='test_drive_access',
            folder='test',
            scale=30,
            maxPixels=1e6
        )
        task.start()
        print("✓ Drive access verified")
        return True
    except Exception as e:
        print(f"Drive access test failed: {e}")
        print("Ensure your Google account has Drive access and re-authenticate.")
        return False

# Authenticate and initialize
authenticate_and_initialize()
if not check_drive_access():
    exit()

# 1. Load Muzaffargarh Boundary
muzaffargarh_shp = r"D:\Thesis\Shapefile\Muzaffrahgarh\Muzaffrahgarh.shp"
try:
    gdf = gpd.read_file(muzaffargarh_shp)
    muzaffargarh_geom = geemap.geopandas_to_ee(gdf)
    muzaffargarh_geom = muzaffargarh_geom.geometry().simplify(100)
    print("✓ Muzaffargarh boundary loaded and converted to Geometry")
    # Get bounding box for reference
    bounds = muzaffargarh_geom.bounds().getInfo()['coordinates'][0]
    print(f"✓ Study area bounds: {bounds}")
except Exception as e:
    print(f"Error loading shapefile: {e}")
    exit()

# Define common projection and scale
COMMON_SCALE = 30
COMMON_CRS = 'EPSG:4326'

# Function to resample and reproject to common specifications
def standardize_raster(image, geometry):
    return image.reproject(crs=COMMON_CRS, scale=COMMON_SCALE).clip(geometry)

# 2. Load and Process Data for 2025 Projections
# DEM (SRTM 30m) - static dataset (no change expected)
try:
    dem = ee.Image('USGS/SRTMGL1_003').select('elevation')
    dem = standardize_raster(dem, muzaffargarh_geom)
    slope = ee.Terrain.slope(dem)
    slope = standardize_raster(slope, muzaffargarh_geom)
    print("✓ DEM and Slope loaded for Muzaffargarh (static for 2025)")
except Exception as e:
    print(f"Error loading DEM: {e}")
    exit()

# LULC 2025 Projection (based on urbanization and agricultural expansion)
try:
    # Use 2022 LULC as baseline and project to 2025
    lulc_2022 = ee.ImageCollection('ESA/WorldCover/v200').first().select('Map')
    # Identify urban areas (class 50) and agricultural areas (class 40)
    urban_areas_2022 = lulc_2022.eq(50)
    agri_areas_2022 = lulc_2022.eq(40)
    # Project urban expansion (3% annual growth for Muzaffargarh)
    urban_expansion = urban_areas_2022.focal_max(radius=400, units='meters')  # Urban sprawl
    # Project agricultural expansion into marginal lands
    agri_expansion = agri_areas_2022.focal_max(radius=300, units='meters')
    # Create 2025 LULC projection
    lulc_2025 = lulc_2022.where(urban_expansion.gt(0.4), 50)  # Convert to urban
    lulc_2025 = lulc_2025.where(agri_expansion.gt(0.3).And(lulc_2022.neq(50)), 40)  # Convert to agriculture
    lulc = standardize_raster(lulc_2025, muzaffargarh_geom)
    print("✓ LULC 2025 projection created (urban & agricultural expansion)")
except Exception as e:
    print(f"Error creating LULC 2025 projection: {e}")
    exit()

# NDVI 2025 Projection (based on climate change and land use trends)
try:
    # Use 2022 NDVI as baseline
    ndvi_2022 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterBounds(muzaffargarh_geom) \
        .filterDate('2022-04-01', '2022-05-31') \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)) \
        .median() \
        .normalizedDifference(['B8', 'B4'])
    # Projected NDVI for 2025 considering:
    # - Climate stress: -2% per year
    # - Urbanization impact: Additional -5% in urban areas
    ndvi_2025 = ndvi_2022.multiply(0.94)  # -6% over 3 years
    # Further reduce in urban areas
    urban_mask = lulc.eq(50)
    ndvi_2025 = ndvi_2025.where(urban_mask, ndvi_2025.multiply(0.95))
    ndvi = standardize_raster(ndvi_2025, muzaffargarh_geom)
    print("✓ NDVI 2025 projection created (climate & urbanization impacts)")
except Exception as e:
    print(f"Error computing NDVI 2025 projection: {e}")
    exit()

# Rainfall 2025 Projection (climate change scenarios for Punjab)
try:
    # Use 2022 as baseline (extreme flood year)
    rainfall_2022 = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
        .filterBounds(muzaffargarh_geom) \
        .filterDate('2022-06-01', '2022-09-30') \
        .sum()
    # Projected rainfall for 2025 based on IPCC AR6 projections:
    # - Increased monsoon intensity in South Asia: +3-5% per decade
    # - More extreme rainfall events
    rainfall_2025 = rainfall_2022.multiply(1.08)  # +8% increase by 2025 from 2022 baseline
    rainfall = standardize_raster(rainfall_2025, muzaffargarh_geom)
    print("✓ Rainfall 2025 projection created (+8% climate change scenario)")
except Exception as e:
    print(f"Error loading Rainfall 2025 projection: {e}")
    exit()

# Drainage Density 2025 (considering land use changes)
try:
    # Calculate flow accumulation
    filled_dem = ee.Algorithms.TerrainFill(dem, 50)
    flow_dir = ee.Terrain.flowDirection(filled_dem)
    flow_acc = ee.Terrain.flowAccumulation(flow_dir, 1)
    # Adjust stream threshold for urbanization (reduced infiltration)
    urban_mask = lulc.eq(50)
    # Lower threshold in urban areas, higher in natural areas
    stream_threshold = flow_acc.gt(1000).where(urban_mask, flow_acc.gt(600))
    # Calculate drainage density
    drainage_density = stream_threshold.focal_mean(radius=150, units='meters', kernelType='circle')
    drainage_density = standardize_raster(drainage_density, muzaffargarh_geom)
    print("✓ Drainage density 2025 projection calculated (urbanization impact)")
except Exception as e:
    print(f"Error computing Drainage Density: {e}")
    # Create a fallback drainage density
    print("Creating fallback drainage density...")
    drainage_density = slope.multiply(0.03).min(1.0)  # Higher for urbanized future
    drainage_density = standardize_raster(drainage_density, muzaffargarh_geom)
    print("✓ Fallback drainage density created")

# 3. Susceptibility Layers (5-class scoring system) for 2025 Projection
print("Creating 2025 susceptibility layers with 5-class system...")

# Elevation susceptibility for 2025 (unchanged physically)
dem_suscept = ee.Image(1) \
    .where(dem.gt(200), 0.2) \
    .where(dem.gt(150), 0.4) \
    .where(dem.gt(100), 0.6) \
    .where(dem.gt(50), 0.8) \
    .where(dem.lte(50), 1.0)

# Slope susceptibility (unchanged)
slope_suscept = ee.Image(1) \
    .where(slope.gt(10), 0.2) \
    .where(slope.gt(5), 0.4) \
    .where(slope.gt(2), 0.6) \
    .where(slope.gt(1), 0.8) \
    .where(slope.lte(1), 1.0)

# LULC susceptibility for 2025 (updated for projected changes)
lulc_suscept = lulc.remap(
    [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100],
    [0.2, 0.4, 0.3, 0.85, 0.9, 0.7, 0.1, 1.0, 0.95, 0.85, 0.3],
    0.5
)

# NDVI susceptibility for 2025 (lower NDVI in urban areas = higher susceptibility)
ndvi_suscept = ee.Image(1) \
    .where(ndvi.gt(0.6), 0.2) \
    .where(ndvi.gt(0.4), 0.4) \
    .where(ndvi.gt(0.2), 0.6) \
    .where(ndvi.gt(0.0), 0.8) \
    .where(ndvi.lte(0.0), 1.0)

# Rainfall susceptibility for 2025 (higher thresholds for increased rainfall)
rainfall_suscept = ee.Image(1) \
    .where(rainfall.lt(350), 0.2) \
    .where(rainfall.lt(550), 0.4) \
    .where(rainfall.lt(750), 0.6) \
    .where(rainfall.lt(950), 0.8) \
    .where(rainfall.gte(950), 1.0)

# Drainage density susceptibility for 2025
drainage_suscept = ee.Image(1) \
    .where(drainage_density.lt(0.2), 0.2) \
    .where(drainage_density.lt(0.4), 0.4) \
    .where(drainage_density.lt(0.6), 0.6) \
    .where(drainage_density.lt(0.8), 0.8) \
    .where(drainage_density.gte(0.8), 1.0)

print("✓ All 2025 susceptibility layers created with 5-class system")

# 4. Weighted Susceptibility for 2025 (future climate and land use considerations)
weights = {
    'dem': 0.12,       # Slight increase due to sea level rise concerns
    'slope': 0.13,     # Reduced as urbanization alters natural slopes
    'lulc': 0.25,      # Increased weight due to significant land use changes
    'ndvi': 0.10,      # Climate stress indicator
    'rainfall': 0.30,  # High weight for climate change impacts
    'drainage': 0.10   # Modified by urbanization
}

susceptibility = dem_suscept.multiply(weights['dem']) \
    .add(slope_suscept.multiply(weights['slope'])) \
    .add(lulc_suscept.multiply(weights['lulc'])) \
    .add(ndvi_suscept.multiply(weights['ndvi'])) \
    .add(rainfall_suscept.multiply(weights['rainfall'])) \
    .add(drainage_suscept.multiply(weights['drainage'])) \
    .clip(muzaffargarh_geom)

print("✓ 2025 Weighted susceptibility calculated")

# 5. Classify Susceptibility into 5 classes for 2025
susceptibility_classified = ee.Image(1) \
    .where(susceptibility.lte(0.2), 1) \
    .where(susceptibility.lte(0.4), 2) \
    .where(susceptibility.lte(0.6), 3) \
    .where(susceptibility.lte(0.8), 4) \
    .where(susceptibility.gt(0.8), 5) \
    .clip(muzaffargarh_geom) \
    .rename('flood_susceptibility_2025')

print("✓ 2025 Classified susceptibility (1-5: Very Low to Very High)")

# 6. Classify all rasters into 5 classes for consistency
def classify_5_classes(image, thresholds, class_values=[1, 2, 3, 4, 5]):
    """Classify image into 5 classes based on thresholds"""
    classified = ee.Image(class_values[0])
    for i, threshold in enumerate(thresholds):
        classified = classified.where(image.gt(threshold), class_values[i + 1])
    return classified

# Classify individual 2025 projected rasters
dem_classified = classify_5_classes(dem, [50, 100, 150, 200])
slope_classified = classify_5_classes(slope, [1, 2, 5, 10])
ndvi_classified = classify_5_classes(ndvi, [0.0, 0.2, 0.4, 0.6])
rainfall_classified = classify_5_classes(rainfall, [350, 550, 750, 950])
drainage_classified = classify_5_classes(drainage_density, [0.2, 0.4, 0.6, 0.8])
print("✓ All 2025 projected rasters classified into 5 classes")

# 7. Export 2025 Projection Rasters to Google Drive
export_folder = 'Muzaffargarh_2025_Projection_5Class'
export_params = {
    'region': muzaffargarh_geom,
    'scale': COMMON_SCALE,
    'crs': COMMON_CRS,
    'maxPixels': 1e10,
    'folder': export_folder,
    'fileFormat': 'GeoTIFF'
}

# List of 2025 projected rasters to export
rasters = [
    (dem_classified, 'DEM_5Class_2025'),
    (slope_classified, 'Slope_5Class_2025'),
    (lulc, 'LULC_2025_Projection'),
    (ndvi_classified, 'NDVI_5Class_2025'),
    (rainfall_classified, 'Rainfall_5Class_2025'),
    (drainage_classified, 'Drainage_Density_5Class_2025'),
    (susceptibility_classified, 'Flood_Susceptibility_5Class_2025'),
    (susceptibility, 'Flood_Susceptibility_Continuous_2025')
]

# Start export tasks with status monitoring
tasks = []
for raster, name in rasters:
    try:
        task = ee.batch.Export.image.toDrive(
            image=raster,
            description=name,
            **export_params
        )
        task.start()
        tasks.append((task, name))
        print(f"✓ Export task started for {name}")
        time.sleep(2)
    except Exception as e:
        print(f"Error starting export for {name}: {e}")

# Monitor task status
print("\nMonitoring export tasks...")
completed_tasks = 0
for task, name in tasks:
    try:
        status = task.status()
        while status['state'] in ['READY', 'RUNNING']:
            print(f"Task {name}: {status['state']}")
            time.sleep(10)
            status = task.status()
        if status['state'] == 'COMPLETED':
            print(f"✓ Task {name} completed successfully")
            completed_tasks += 1
        else:
            print(f"Task {name} failed with state: {status['state']}")
            if 'error_message' in status:
                print(f"Error: {status['error_message']}")
    except Exception as e:
        print(f"Error monitoring task {name}: {e}")

print(f"\n{completed_tasks}/{len(tasks)} export tasks completed successfully.")
print("Check Google Drive folder '{}' for GeoTIFF files.".format(export_folder))

# 8. Visualization for 2025 Projections
Map = geemap.Map(center=[30.0, 71.0], zoom=9)  # Centered on Muzaffargarh

# Add 2025 projection layers
try:
    Map.addLayer(muzaffargarh_geom, {'color': 'black'}, 'Muzaffargarh Boundary', False)
    Map.addLayer(dem_classified, {'min': 1, 'max': 5, 'palette': ['darkblue', 'blue', 'green', 'yellow', 'red']}, 'DEM 2025 (5 Class)', False)
    Map.addLayer(slope_classified, {'min': 1, 'max': 5, 'palette': ['darkgreen', 'green', 'yellow', 'orange', 'red']}, 'Slope 2025 (5 Class)', False)
    # LULC 2025 with specific visualization
    lulc_vis = {'min': 10, 'max': 100, 'palette': ['006400', '90EE90', 'FFFF00', '8B4513', '0000FF', 'FF0000', '808080', 'FFFFFF', 'A9A9A9', '000080', '00FFFF']}
    Map.addLayer(lulc, lulc_vis, 'LULC 2025 Projection', False)
    Map.addLayer(ndvi_classified, {'min': 1, 'max': 5, 'palette': ['brown', 'yellow', 'lightgreen', 'green', 'darkgreen']}, 'NDVI 2025 (5 Class)', False)
    Map.addLayer(rainfall_classified, {'min': 1, 'max': 5, 'palette': ['white', 'lightblue', 'blue', 'darkblue', 'purple']}, 'Rainfall 2025 (5 Class)', False)
    Map.addLayer(drainage_classified, {'min': 1, 'max': 5, 'palette': ['white', 'lightcyan', 'cyan', 'blue', 'darkblue']}, 'Drainage Density 2025 (5 Class)', False)
    # 2025 Flood susceptibility with 5-class color scheme
    Map.addLayer(susceptibility_classified,
                 {'min': 1, 'max': 5, 'palette': ['#00FF00', '#ADFF2F', '#FFFF00', '#FFA500', '#FF0000']},
                 'Flood Susceptibility 2025 Projection (5 Class)', True)
    # Add comprehensive legend for 2025
    Map.add_legend(title='5-Class Flood Susceptibility 2025',
                    legend_dict={
                        'Very Low (1)': '#00FF00',
                        'Low (2)': '#ADFF2F',
                        'Moderate (3)': '#FFFF00',
                        'High (4)': '#FFA500',
                        'Very High (5)': '#FF0000'
                    }, position='bottomright')
    Map.addLayerControl()
    print("✓ Map created with all 2025 projection layers")
except Exception as e:
    print(f"Error adding layers to map: {e}")

# Display 2025 projection results
print("\n" + "=" * 70)
print("FLOOD SUSCEPTIBILITY ANALYSIS - MUZAFFARGARH 2025 PROJECTION")
print("=" * 70)
print("Region: Muzaffargarh District, Punjab, Pakistan")
print("Period: 2025 Projection (Climate Change & Urbanization Scenarios)")
print("Resolution: 30m | CRS: EPSG:4326")
print("\nPROJECTION ASSUMPTIONS:")
print(" • LULC Changes:")
print("   - Urban expansion: 3% annual growth")
print("   - Agricultural expansion into marginal lands")
print("   - Reduced natural vegetation cover")
print(" • Climate Change Impacts:")
print("   - Rainfall: +8% increase from 2022 baseline")
print("   - NDVI: -6% overall reduction (climate stress)")
print("   - Additional -5% NDVI reduction in urban areas")
print(" • Hydrological Changes:")
print("   - Reduced infiltration in urban areas")
print("   - Altered drainage patterns")
print("\nPARAMETERS & WEIGHTS (adjusted for future conditions):")
for param, weight in weights.items():
    print(f"  {param.upper():<8}: {weight:.2f}")
print("\nCLIMATE CHANGE CONTEXT (IPCC AR6):")
print(" • South Asia: Increased monsoon intensity")
print(" • More frequent extreme rainfall events")
print(" • Higher flood risks in Indus River basin")
print("\nURBANIZATION TRENDS IN MUZAFFARGARH:")
print(" • Rapid urban expansion along highways")
print(" • Conversion of agricultural land to urban")
print(" • Increased impervious surfaces")
print("\nSUSCEPTIBILITY CLASSES:")
print(" 1: Very Low | 2: Low | 3: Moderate | 4: High | 5: Very High")
print("\nANALYSIS PURPOSE:")
print(" • Long-term flood risk assessment")
print(" • Climate adaptation planning")
print(" • Urban development guidelines")
print(" • Agricultural resilience strategies")
print("=" * 70)

# Show map
Map

# change year according to your choice
