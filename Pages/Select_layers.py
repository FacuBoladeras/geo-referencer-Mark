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
import matplotlib.pyplot as plt
from adjustText import adjust_text
from PIL import Image
import folium
from streamlit_folium import st_folium ,folium_static
from folium.plugins import Draw
import numpy as np
from geojson import FeatureCollection

#########  Streamlit config  ##########

st.set_page_config(
    page_title="Select Layers",
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
##########################################################

st.sidebar.title("🔘 Select Layers")
st.sidebar.info(" 1. Upload the DXF file  \n 2. Select the layers to be added to the geojson")

st.info("Allow to select the layer with the information to added to the geojson")
uploaded_file = st.file_uploader(
"Choose a DXF file", accept_multiple_files=False, type="dxf", key="2")
if uploaded_file is not None:
    with st.spinner('Uploading files ...'):
        file = uploaded_file
        gdf , file_name = dxf_to_gdf(file)
        gdf_pol = gdf[gdf['geometry'].type.isin(
            ['Polygon', 'MultiPolygon','LineString'])]
        
        gdf_point = gdf[gdf['geometry'].type.isin(
            ['Point'])]

        # get name of the layers
        layers_pol = gdf_pol['Layer'].unique()
        layers_point = gdf_point['Layer'].unique()

        #add selector
        prob_name = ['70-spaces','002-Net_room_area_polylines']
        
        for item in prob_name:
            if item in layers_pol:
                index = layers_pol.tolist().index(item)
                break
            else:
                index = 0

        layer_pol = st.selectbox('Select polygon layer (area)', layers_pol,index=index)
        gdf_spaces = gdf_pol[gdf_pol['Layer'] == layer_pol]
        gdf_pol = gpd.GeoSeries(polygonize(gdf_spaces.geometry))
        gdf_pol = gpd.GeoDataFrame(gdf_pol, columns=['geometry'])

        fig, ax = plt.subplots(figsize=(7, 7))
        gdf_pol.plot(ax=ax, color='blue',
                        alpha=0.5, edgecolor='k', linewidth=0.5)
        plt.axis('off')

        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        img = Image.open(buf)
        nonwhite_positions = [(x,y) for x in range(img.size[0]) for y in range(img.size[1]) if img.getdata()[x+y*img.size[0]] != (255,255,255,255)]
        rect = (min([x for x,y in nonwhite_positions])-10, min([y for x,y in nonwhite_positions])-10, max([x for x,y in nonwhite_positions])+10, max([y for x,y in nonwhite_positions])+10)
        croped = img.crop(rect)
        st.image(croped, output_format='PNG', use_column_width=False)
        # st.pyplot(buf,clear_figure=True)

        ppoint_name = ['71-spaces_data','003-Room_number_text']
        
        for item in ppoint_name:
            if item in layers_point:
                index = layers_point.tolist().index(item)
                break
            else:
                index = 0
        layer_point = st.selectbox('Select point layer (propertie)', layers_point , index=index)
        gdf_points = gdf_point[gdf_point['Layer'] == layer_point]

        # remove geometry from the geodataframe
        df_points = gdf_points.drop(columns=['geometry'])
        # df_points = df_points.style.hide_index()

        df_points_columns = df_points.columns
        
        prob_name = ['Text']
        for item in prob_name:
            if item in df_points_columns:
                index = df_points_columns.tolist().index(item)
                break
            else:
                index = 0

        st.selectbox('Select Attribute to add', df_points_columns, index=index)
        
        # show only the items where "SubClasses" has "Attribute" in it
        gdf_points = gdf_points[gdf_points['SubClasses'].str.contains("Attribute")]

        ###################   DOWNLOAD GEOJSON   ###################

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
            spaceid = feat['properties']['prop']
            if isinstance(spaceid,list):
                if spaceid:
                    spaceid = spaceid[0]
                else:
                    spaceid = None

            feat['id'] = spaceid
            feat['properties'] = {
                "Layer": layer_pol,
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
                        file_name=file_name[0:-4]+'.geojson', key='d2')
        
        ############   show table  ############

        st.table(gdf_points.drop(columns=['geometry']))
        
        ##########   PLOT POINTS   ##########

        # fig, ax = plt.subplots()
        # ax = gdf_points.plot(ax=ax, color='blue', marker='o', markersize=4,
        #                 alpha=0.5, edgecolor='k', linewidth=0.5, )

        # gdf_points['coords'] = gdf_points['geometry'].apply(lambda x: x.representative_point().coords[:])
        # gdf_points['coords'] = [coords[0][:2] for coords in gdf_points['coords']]
        # texts = []
        # for idx, row in gdf_points.iterrows():
        #     texts.append(ax.text(row['coords'][0], row['coords'][1], row['Text'], fontsize = 5))
        # adjust_text(texts,ax=ax, arrowprops=dict(arrowstyle="-", color='k', lw=0.5))

        # plt.axis('off')
        # st.pyplot()