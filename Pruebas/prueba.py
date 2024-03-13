import geopandas as gpd
from shapely.geometry import shape, Polygon
import json

def dxf_to_geojson(file_path):
    gdf = gpd.read_file(file_path)
    # Filter geometries based on layer name
    gdf_spaces = gdf[(gdf['Layer'] == '70-spaces') | (gdf['Layer'] == '002-Net_room_area_polylines')]

    if gdf_spaces.empty:
        return None

    # Convert polygon geometries to GeoDataFrame
    polygons = []
    for geom in gdf_spaces['geometry']:
        if isinstance(geom, Polygon):
            polygons.append(geom)
        elif geom.geom_type == 'MultiPolygon':
            polygons.extend(list(geom))
    
    gdf_pol = gpd.GeoDataFrame(geometry=polygons)
    
    # Get properties
    gdf_points = gdf[(gdf['Layer'] == '71-spaces_data') | (gdf['Layer'] == '003-Room_number_text')]
    if gdf_points.empty:
        return None

    text_prop = []
    for i, pol in gdf_pol.iterrows():
        gdf_inter = gdf_points.overlay(gpd.GeoDataFrame(geometry=[pol['geometry']]), how='intersection')
        prop = gdf_inter['Text'].tolist()
        text_prop.append(prop)

    gdf_pol['prop'] = text_prop

    # Create GeoJSON feature collection
    features = []
    for i, row in gdf_pol.iterrows():
        feature = {
            "type": "Feature",
            "geometry": json.loads(row['geometry'].to_json()),
            "properties": {
                "Layer": "70-spaces",
                "type": "area.space",
                "custom": "[object Object]",
                "PaperSpace": None,
                "SubClasses": "AcDbEntity:AcDbPolyline",
                "Linetype": "Continuous",
                "EntityHandle": "2A546",
                "Text": row['prop'],
                "name": "Space"
            }
        }
        features.append(feature)
    
    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }

    return geojson_data

# Usage example:
file_path = "C:\\Users\\Facu\\Desktop\\geo-referencer-Mark\\New folder\\ACME_1_00.dxf"
geojson_data = dxf_to_geojson(file_path)

if geojson_data is not None:
    with open("output.geojson", "w") as f:
        json.dump(geojson_data, f)
        print("Conversion successful! GeoJSON saved.")
else:
    print("Error: No valid geometries found in DXF file.")
