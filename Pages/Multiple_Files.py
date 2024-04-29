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

#########  Streamlit config  ##########

st.set_page_config(
    page_title="Convert multiple files",
    page_icon="favicon.ico",
    # layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://your-site.com/bug-report',
        'Report a bug': "https://your-site.com/bug-report",
        'About': "Powered by <Company>!"
    },
)
st.set_option('deprecation.showPyplotGlobalUse', False)

with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

hide_table_row_index = """
    <style>
    thead tr th:first-child {display:none}
    tbody th {display:none}
    </style>
    """
st.markdown(hide_table_row_index, unsafe_allow_html=True)


st.cache_resource(max_entries=10, ttl=3600,)

def extract_properties(gdf):
    
    def properties_to_dict(props):
        return dict(props)

    properties_df = gdf['properties'].apply(properties_to_dict).apply(pd.Series)

    return properties_df

def dxf_to_gdf(file):
    file_name = file.name
    bytes_data = file.getvalue()
    with MemoryFile(bytes_data) as memfile:
        with memfile.open() as src:
            df1 = gpd.GeoDataFrame(src)
            
            
            def is_valid(geom):
                try:
                    geom_type = geom.geom_type
                    return geom_type == 'Polygon' or geom_type == 'LineString' or geom_type == 'Point'
                except AttributeError:
                    return False

            df1['isvalid'] = df1['geometry'].apply(lambda x: is_valid(x))
            df1 = df1[df1['isvalid']]

            gdf = gpd.GeoDataFrame.from_features(df1)
            properties_df = extract_properties(gdf)

            
            gdf = pd.concat([gdf, properties_df], axis=1)            
            gdf.drop(columns=['properties'], inplace=True)
            print(gdf.head())
            gdf.info()
            gdf.head(2)
            return gdf, file_name


# declare state variables
st.sidebar.title("📂 Convert multiple files")
st.sidebar.info("Upload multiple files at once and convert them to GeoJSON")
st.title("Conversion Tool")

st.info("Upload multiple files at once")
uploaded_file = st.file_uploader(
"Choose a DXF file ", accept_multiple_files=True, type="dxf" , key="1")
if uploaded_file is not None:
    with st.spinner('Loading ...'):
        for i, file in enumerate(uploaded_file):
            gdf , file_name = dxf_to_gdf(file)
            gdf_spaces = gdf[gdf['Layer'] == '70-spaces']

            if gdf_spaces.empty:
                gdf_spaces = gdf[gdf['Layer'] ==
                                '002-Net_room_area_polylines']

            gdf_pol = gpd.GeoSeries(polygonize(gdf_spaces.geometry))
            gdf_pol = gpd.GeoDataFrame(gdf_pol, columns=['geometry'])

            fig, ax = plt.subplots()
            ax = gdf_pol.plot(ax=ax, color='blue',
                            alpha=0.5, edgecolor='k', linewidth=0.5)
            plt.axis('off')
            st.pyplot()

            ######  Get properties  ######

            # '003-Room_number_text','72-spaces_usage'
            gdf_points = gdf[gdf['Layer'] == '71-spaces_data']
            if gdf_points.empty:
                gdf_points = gdf[gdf['Layer']
                                == '003-Room_number_text']
                list_index = 0
            else:
                list_index = 1

            text_prop = []
            gdf_inter = None
            for i, item in gdf_pol.iterrows():
                gdf_inter = gdf_points.overlay(
                    gdf_pol.loc[[i]], how='intersection')
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
                                    "name": "Space"}

            geojson = json.dumps(featcoll)
            st.download_button('Download GeoJson', geojson, mime='text/json',
                            file_name=file_name[0:-4]+'.geojson', key=str(i))