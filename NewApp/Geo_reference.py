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

def mainGeo():
    
    st.set_option('deprecation.showPyplotGlobalUse', False)
    st.cache_resource(max_entries=10, ttl=3600,)

    if 'fg' not in st.session_state:
        st.session_state['fg'] = folium.FeatureGroup(name="Markers",)

    if 'feat' not in st.session_state:
        st.session_state['feat'] = None 

    if 'first_run' not in st.session_state:
        st.session_state['first_run'] = True

    if 'center' not in st.session_state:
        st.session_state['center'] = {'lat': 52.156046, 'lng': 5.587156}

    if 'zoom' not in st.session_state:
        st.session_state['zoom'] = 10

    if 'file_uploaded' not in st.session_state:
        st.session_state['file_uploaded'] = False

    if 'down_button' not in st.session_state:
        st.session_state['down_button'] = False

    if 'feattodownload' not in st.session_state:
        st.session_state['feattodownload'] = {'type': 'FeatureCollection', 'features': []}

    if 'file_name' not in st.session_state:
        st.session_state['file_name'] = "floorplan.geojson"

    if 'show_uploaded_legend' not in st.session_state:
        st.session_state['show_uploaded_legend'] = True

    st.sidebar.title("🌍 Geo Reference Floor Plan")
    info = """ 1.- Choose the GeoJSON file and Click on the UPLOAD button \n \\
            2.- Draw a polygon on the map \n \\
            3.- Click on the Accept button to bring the floorplan into the map \n \\
            4.- Use the slider to adjust size, rotation and position \n \\
            5.- Download the GeoJSON file with geographical coordinates \n
    """
    st.sidebar.info(info)

    st.info("Allow to project the GeoJSON file to geographic coordinates.")
    # uploaded_file = st.file_uploader(
    #     "Choose a GeoJSON file", accept_multiple_files=False, type="geojson", key='upload_button')

    with st.form("my-form", clear_on_submit=True):
        uploaded_file = st.file_uploader(
        "Choose a GeoJSON file", accept_multiple_files=False, type="geojson", key='upload_button')
        submitted = st.form_submit_button("Click to UPLOAD!")
        if submitted:
            st.session_state['show_uploaded_legend'] = True

        if uploaded_file is not None and st.session_state['show_uploaded_legend']:
            st.write("UPLOADED! "+uploaded_file.name)

    fig, ax = plt.subplots()
    if uploaded_file is not None:
        with st.spinner('Uploading files ...'):
            # convert uploaded file to geodataframe
            st.session_state['file_uploaded'] = True
            bytes_data = uploaded_file.getvalue()
            st.session_state['file_name'] = uploaded_file.name
            gdf_plan = gpd.read_file(io.BytesIO(bytes_data))
            gdf_plan.set_crs(epsg=4326,allow_override=True, inplace=True)
            # fix non valid polygons
            gdf_plan.geometry = gdf_plan.geometry.apply(lambda x: x.buffer(0.001))
            gdf_plan = gdf_plan[gdf_plan.geometry.is_valid]

    # Map
    feat = st.session_state['feat']
    location = [st.session_state['center']['lat'], st.session_state['center']['lng']]
    m = folium.Map(location=location,zoom_start=11, tiles=None)
    fg = folium.FeatureGroup(name="draw",)
    folium.TileLayer('OpenStreetMap',overlay=True, zoom_start=10, max_zoom=22,max_native_zoom=19).add_to(m)
    folium.LayerControl().add_to(m)

    if st.session_state['first_run']:
        Draw(export=False, draw_options={'circle':False,'polyline':False,'circlemarker':False}).add_to(m)

    angle = st.sidebar.slider('angle', min_value=0, max_value=360, value=0, step=1)
    x_slide = st.sidebar.slider('x', min_value=-10, max_value=10, value=0, step=1)
    y_slide = st.sidebar.slider('y', min_value=-10, max_value=10, value=0, step=1)
    scale_slide = st.sidebar.slider('scale', min_value=0.5, max_value=1.5, value=1.0, step=0.05)

    if feat is not None:
        gdf = gpd.GeoDataFrame.from_features(feat)
        gdf.crs = 'epsg:4326'
        gdf.to_crs(epsg=3857, inplace=True)
        centroid = gdf.dissolve().geometry.centroid.values[0]    
        gdf.geometry = gdf.geometry.apply(lambda x: rotate(x, angle=angle , origin=centroid))
        gdf.geometry = gdf.geometry.apply(lambda x: translate(x, xoff=x_slide, yoff=y_slide))
        gdf.geometry = gdf.geometry.apply(lambda x: scale(x, xfact=scale_slide, yfact=scale_slide, origin=centroid))
        gdf.to_crs(epsg=4326, inplace=True)
        folium.GeoJson(gdf.__geo_interface__).add_to(fg)
        st.session_state['feattodownload'] = gdf.__geo_interface__
        
        
    else:
        None

    st_data = st_folium(m ,
                        key='map5',
                        center=st.session_state["center"],
                        zoom=st.session_state["zoom"],
                        width=700, height=750,
                        feature_group_to_add=fg)

    if st_data['last_active_drawing'] is not None and st.session_state['file_uploaded']:
        click_disable = False
    else:
        click_disable = True


    click = st.button('Accept', disabled=click_disable)

    if click:
        st.session_state['down_button'] = True
        st.session_state["zoom"] = st_data['zoom']
        st.session_state["center"] = st_data['center']

        poly = st_data['last_active_drawing']
        # get length and width of polygon
        if poly is not None:
            poly = Polygon(poly['geometry']['coordinates'][0])
            box = poly.minimum_rotated_rectangle
            x, y = box.exterior.coords.xy
            edge_length = (Point(x[0], y[0]).distance(Point(x[1], y[1])), Point(x[1], y[1]).distance(Point(x[2], y[2])))
            length = max(edge_length)
            width = min(edge_length)
            centroid = poly.centroid

        # dissolve
        gdf_diss = gdf_plan.dissolve()

        # get length and width of plan
        poly_plan = gdf_diss.geometry.values[0]
        poly_plan = poly_plan.buffer(0.001)
        box = poly_plan.minimum_rotated_rectangle
        x, y = box.exterior.coords.xy
        edge_length = (Point(x[0], y[0]).distance(Point(x[1], y[1])), Point(x[1], y[1]).distance(Point(x[2], y[2])))
        length_plan = max(edge_length)
        width_plan = min(edge_length)

        # get centroid
        centroid_plan = gdf_diss.centroid.values[0]
        # get scale
        sc_factor = length / length_plan

        # scale geometry plan
        gdf_plan.geometry = gdf_plan.geometry.apply(lambda x: scale(x, xfact=sc_factor, yfact=sc_factor, origin=centroid_plan))

        # translate geometry plan
        x_slide = centroid.x - centroid_plan.x
        y_slide = centroid.y - centroid_plan.y

        gdf_plan.geometry = gdf_plan.geometry.apply(lambda x: translate(x, xoff=x_slide, yoff=y_slide))

        plan_feat = gdf_plan.__geo_interface__


        # at the end set crs 4326

        st.session_state['feat'] = plan_feat['features'] #[st_data['last_active_drawing']]

        if st.session_state['first_run']:
            st.session_state['first_run'] = False
            st.experimental_rerun()



    # Download button
    # if st.session_state['down_button']:

    if st.session_state['down_button']:
        disabled = False
    else:
        disabled = True

    filename = st.session_state['file_name']

    featcoll = st.session_state['feattodownload']
    geojson = json.dumps(featcoll)

    col1, col2 = st.sidebar.columns(2)

    with col1:

        st.download_button(label=f'{filename[:-8]}_geo.geojson', data=geojson ,
                                    file_name=f'{filename[:-8]}_geo.geojson', mime='text/json',
                                    disabled=disabled, key='download_button')

        if st.session_state['download_button']:
            None

    with col2:

        if st.button(label='Reset Map', key='reset_button'):
            st.session_state['feat'] = None
            st.session_state['first_run'] = True
            st.session_state['down_button'] = False
            st.session_state['show_uploaded_legend'] = False
            st.experimental_rerun()
        




if __name__ == "__main__":
    mainGeo()