import warnings
warnings.filterwarnings("ignore")
import streamlit as st
import json
import fiona
from shapely.geometry import shape
import pandas as pd
import geopandas as gpd
from shapely.ops import polygonize
from shapely.geometry import Point, Polygon, LineString, MultiPolygon
from shapely.affinity import scale, rotate, translate
import os
from fiona.io import MemoryFile, ZipMemoryFile
import io
from io import BytesIO
import matplotlib.pyplot as plt
from adjustText import adjust_text
from PIL import Image
import folium
from streamlit_folium import st_folium ,folium_static
from folium.plugins import Draw
import numpy as np
from geojson import FeatureCollection
from .FuncionCapas import select_and_visualize_layers


def extract_properties(gdf):
    def properties_to_dict(props):
        return dict(props)

    properties_df = gdf['properties'].apply(properties_to_dict).apply(pd.Series)
    return properties_df

@st.cache_data
def dxf_to_gdf(file):
    file_name = file.name
    bytes_data = file.getvalue()
    with MemoryFile(bytes_data) as memfile:
        with memfile.open() as src:
            df1 = gpd.GeoDataFrame(src)
            
            def is_valid(geom):
                try:
                    geom_type = geom.geom_type
                    return geom_type in ['Polygon', 'LineString', 'Point']
                except AttributeError:
                    return False
            
            df1['isvalid'] = df1['geometry'].apply(lambda x: is_valid(x))
            df1 = df1[df1['isvalid']]
            
            gdf = gpd.GeoDataFrame.from_features(df1)
            properties_df = extract_properties(gdf)
            
            gdf = pd.concat([gdf, properties_df], axis=1)            
            gdf.drop(columns=['properties'], inplace=True)
            
            return gdf, file_name

def process_properties(gdf_pol, gdf, file_name):
    gdf_points = gdf[gdf['Layer'] == '71-spaces_data']
    if gdf_points.empty:
        gdf_points = gdf[gdf['Layer'] == '003-Room_number_text']
        list_index = 0
    else:
        list_index = 1

    text_prop = []
    for i, item in gdf_pol.iterrows():
        gdf_inter = gdf_points.overlay(gdf_pol.loc[[i]], how='intersection')
        prop = gdf_inter['Text'].to_list()
        text_prop.append(prop)

    gdf_pol['prop'] = text_prop
    featcoll = gdf_pol.__geo_interface__

    type_prop = "area.space"
    custom_prop = "[object Object]"
    for i, feat in enumerate(featcoll['features']):
        spaceid = feat['properties']['prop'][list_index]
        feat['id'] = spaceid
        feat['properties'] = {
            "Layer": "70-spaces",
            "type": type_prop,
            "custom": custom_prop,
            "PaperSpace": None,
            "SubClasses": "AcDbEntity:AcDbPolyline",
            "Linetype": "Continuous",
            "EntityHandle": "2A546",
            "Text": None,
            "name": "Space"
        }

    geojson = json.dumps(featcoll)
    return geojson, file_name[0:-4] + '.geojson'


def mainFiles():
    st.set_option('deprecation.showPyplotGlobalUse', False)
    st.sidebar.title("📂 Convert multiple files")
    st.sidebar.info("Upload multiple files at once and convert them to GeoJSON")
    st.title("Conversion Tool")

    uploaded_files = st.file_uploader("Choose DXF files", accept_multiple_files=True, type="dxf", key="1")

    if uploaded_files is not None:
        total_files = len(uploaded_files)
        for i, file in enumerate(uploaded_files):
            progress_bar = st.progress((i + 1) / total_files)
            try:
                gdf, file_name = dxf_to_gdf(file)

                gdf_spaces = gdf[gdf['Layer'] == '70-spaces']
                if not gdf_spaces.empty:
                    gdf_pol = gpd.GeoSeries(polygonize(gdf_spaces.geometry))
                    gdf_pol = gpd.GeoDataFrame(gdf_pol, columns=['geometry'])
                else:
                    st.warning("Layer '70-spaces' not found. Selecting another layer...")
                    gdf_spaces = select_and_visualize_layers(gdf)
                    gdf_pol = gpd.GeoSeries(polygonize(gdf_spaces.geometry))
                    gdf_pol = gpd.GeoDataFrame(gdf_pol, columns=['geometry'])

                fig, ax = plt.subplots()
                ax = gdf_pol.plot(ax=ax, color='blue', alpha=0.5, edgecolor='k', linewidth=0.5)
                plt.axis('off')
                st.pyplot()

                geojson, geojson_filename = process_properties(gdf_pol, gdf, file_name)

                download_button_key = f"download_button_{i}"
                st.download_button('Download GeoJson', geojson, mime='text/json', file_name=geojson_filename, key=download_button_key, type="primary")

            except IndexError as e:
                st.warning("There was an error trying to access the layer")
            finally:
                pass
                progress_bar.empty()  # Limpiar la barra de progreso después de completar cada archivo

if __name__ == "__main__":
    mainFiles()
