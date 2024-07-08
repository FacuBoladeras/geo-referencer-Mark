import json
import io
import folium
import geopandas as gpd
import streamlit as st
from shapely.geometry import Polygon, Point
from shapely.affinity import rotate, translate, scale
from streamlit_folium import st_folium
from folium.plugins import Draw
import matplotlib.pyplot as plt

@st.cache_data(max_entries=10, ttl=3600)
def load_geojson_files(uploaded_files):
    gdfs = []
    for uploaded_file in uploaded_files:
        bytes_data = uploaded_file.getvalue()
        gdf = gpd.read_file(io.BytesIO(bytes_data))
        gdf.set_crs(epsg=4326, allow_override=True, inplace=True)
        gdf.geometry = gdf.geometry.apply(lambda x: x.buffer(0.001))
        gdf = gdf[gdf.geometry.is_valid]
        gdfs.append(gdf)
    return gdfs

def initialize_session_state():
    defaults = {
        'fg': folium.FeatureGroup(name="Markers"),
        'feats': [],
        'first_run': True,
        'center': {'lat': 52.156046, 'lng': 5.587156},
        'zoom': 10,
        'files_uploaded': False,
        'down_button': False,
        'feattodownload': {'type': 'FeatureCollection', 'features': []},
        'feattodownloads': {},
        'file_names': [],
        'show_uploaded_legend': True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def display_sidebar():
    st.sidebar.title("🌍 Geo Reference Floor Plan")
    info = """
    **1.- Choose the GeoJSON files and Click on the UPLOAD button** \n \\
    **2.- Draw a polygon on the map; once generated, press cancel to keep only one polygon.** \n \\
    **3.- Click on the Accept button to bring the floorplans into the map** \n \\
    **4.- Use the slider to adjust size, rotation and position** \n \\
    **5.- Download the GeoJSON file with geographical coordinates** \n
    """
    st.sidebar.markdown(info)

def upload_files():
    uploaded_files = st.file_uploader(
        "Choose GeoJSON files", accept_multiple_files=True, type="geojson", key='upload_button')

    if uploaded_files:
        st.session_state['show_uploaded_legend'] = True
        st.session_state['files_uploaded'] = True
        st.session_state['file_names'] = [file.name for file in uploaded_files]
        gdf_plans = load_geojson_files(uploaded_files)
        st.session_state['gdf_plans'] = gdf_plans

def create_map():
    location = [st.session_state['center']['lat'], st.session_state['center']['lng']]
    m = folium.Map(location=location, zoom_start=11, tiles=None)
    fg = folium.FeatureGroup(name="draw")
    folium.TileLayer('OpenStreetMap', overlay=True, zoom_start=10, max_zoom=22, max_native_zoom=19).add_to(m)
    folium.LayerControl().add_to(m)

    if st.session_state['first_run']:
        Draw(export=False, draw_options={'circle': False, 'polyline': False, 'circlemarker': False}).add_to(m)
    return m, fg

def adjust_features(feats, angle, x_slide, y_slide, scale_slide, fg):
    for feat in feats:
        gdf = gpd.GeoDataFrame.from_features(feat)
        gdf.crs = 'epsg:4326'
        gdf.to_crs(epsg=3857, inplace=True)
        centroid = gdf.dissolve().geometry.centroid.values[0]
        gdf.geometry = gdf.geometry.apply(lambda x: rotate(x, angle=angle, origin=centroid))
        gdf.geometry = gdf.geometry.apply(lambda x: translate(x, xoff=x_slide, yoff=y_slide))
        gdf.geometry = gdf.geometry.apply(lambda x: scale(x, xfact=scale_slide, yfact=scale_slide, origin=centroid))
        gdf.to_crs(epsg=4326, inplace=True)
        folium.GeoJson(gdf.__geo_interface__).add_to(fg)
    st.session_state['feattodownload'] = {'type': 'FeatureCollection', 'features': [f for feat in feats for f in feat['features']]}

def handle_accept(st_data):
    st.session_state['down_button'] = True
    st.session_state["zoom"] = st_data['zoom']
    st.session_state["center"] = st_data['center']

    poly = st_data['last_active_drawing']
    if poly is not None:
        poly = Polygon(poly['geometry']['coordinates'][0])
        box = poly.minimum_rotated_rectangle
        x, y = box.exterior.coords.xy
        edge_length = (Point(x[0], y[0]).distance(Point(x[1], y[1])), Point(x[1], y[1]).distance(Point(x[2], y[2])))
        length = max(edge_length)
        width = min(edge_length)
        centroid = poly.centroid

    feats = []
    feattodownloads = {}
    for i, gdf_plan in enumerate(st.session_state['gdf_plans']):
        gdf_diss = gdf_plan.dissolve()
        poly_plan = gdf_diss.geometry.values[0].buffer(0.001)
        box = poly_plan.minimum_rotated_rectangle
        x, y = box.exterior.coords.xy
        edge_length = (Point(x[0], y[0]).distance(Point(x[1], y[1])), Point(x[1], y[1]).distance(Point(x[2], y[2])))
        length_plan = max(edge_length)
        width_plan = min(edge_length)

        centroid_plan = gdf_diss.centroid.values[0]
        sc_factor = length / length_plan

        gdf_plan.geometry = gdf_plan.geometry.apply(lambda x: scale(x, xfact=sc_factor, yfact=sc_factor, origin=centroid_plan))
        x_slide = centroid.x - centroid_plan.x
        y_slide = centroid.y - centroid_plan.y
        gdf_plan.geometry = gdf_plan.geometry.apply(lambda x: translate(x, xoff=x_slide, yoff=y_slide))
        plan_feat = gdf_plan.__geo_interface__
        feats.append(plan_feat)

        # Store each GeoJSON separately
        filename = st.session_state['file_names'][i]
        feattodownloads[filename] = json.dumps(plan_feat)

    st.session_state['feats'] = feats
    st.session_state['feattodownloads'] = feattodownloads

    if st.session_state['first_run']:
        st.session_state['first_run'] = False
        st.rerun()

def download_buttons():
    featcolls = st.session_state['feattodownloads']
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        for i, (filename, geojson) in enumerate(featcolls.items()):
            st.download_button(label=f'{filename}', data=geojson,
                               file_name=f'{filename}', mime='text/json',
                               disabled=not st.session_state['down_button'], key=f'download_button_{i}', type="primary")

    with col2:
        if st.button(label='Reset Map', key='reset_button', type="primary"):
            st.session_state['feats'] = []
            st.session_state['first_run'] = True
            st.session_state['down_button'] = False
            st.session_state['show_uploaded_legend'] = False
            st.rerun()

def mainGeo():
    st.set_option('deprecation.showPyplotGlobalUse', False)

    initialize_session_state()
    display_sidebar()
    upload_files()

    fig, ax = plt.subplots()
    m, fg = create_map()

    angle = st.sidebar.slider('angle', min_value=0, max_value=360, value=0, step=1)
    x_slide = st.sidebar.slider('x', min_value=-10, max_value=10, value=0, step=1)
    y_slide = st.sidebar.slider('y', min_value=-10, max_value=10, value=0, step=1)
    scale_slide = st.sidebar.slider('scale', min_value=0.5, max_value=1.5, value=1.0, step=0.05)

    if st.session_state['feats']:
        adjust_features(st.session_state['feats'], angle, x_slide, y_slide, scale_slide, fg)

    st_data = st_folium(m, key='map5', center=st.session_state["center"], zoom=st.session_state["zoom"],
                        width=700, height=750, feature_group_to_add=fg)

    if st_data['last_active_drawing'] is not None and st.session_state['files_uploaded']:
        click_disable = False
    else:
        click_disable = True

    if st.button('Accept', disabled=click_disable, type="primary"):
        handle_accept(st_data)

    download_buttons()
