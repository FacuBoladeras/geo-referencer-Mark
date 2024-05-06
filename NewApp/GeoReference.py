import streamlit as st
import folium
import geopandas as gpd
import io
import json
import matplotlib.pyplot as plt
from folium.plugins import Draw
from shapely.geometry import Polygon, Point
from shapely.affinity import rotate, translate, scale
from streamlit_folium import st_folium ,folium_static



def setup_session_state():
    session_state_vars = {
        'fg': folium.FeatureGroup(name="Markers"),
        'feat': None,
        'first_run': True,
        'center': {'lat': 52.156046, 'lng': 5.587156},
        'zoom': 10,
        'file_uploaded': False,
        'down_button': False,
        'feattodownload': {'type': 'FeatureCollection', 'features': []},
        'file_name': "floorplan.geojson",
        'show_uploaded_legend': True
    }

    for key, value in session_state_vars.items():
        if key not in st.session_state:
            st.session_state[key] = value


def display_sidebar_info():
    st.sidebar.title("🌍 Geo Reference Floor Plan")
    info = """ 
    1. Choose the GeoJSON file and Click on the UPLOAD button
    2. Draw a polygon on the map
    3. Click on the Accept button to bring the floorplan into the map
    4. Use the slider to adjust size, rotation and position
    5. Download the GeoJSON file with geographical coordinates
    """
    st.sidebar.info(info)


def upload_geojson_file():
    with st.form("my-form", clear_on_submit=True):
        uploaded_file = st.file_uploader(
            "Choose a GeoJSON file", accept_multiple_files=False, type="geojson", key='upload_button')
        submitted = st.form_submit_button("Click to UPLOAD!")
        if submitted:
            st.session_state['show_uploaded_legend'] = True

        if uploaded_file is not None and st.session_state['show_uploaded_legend']:
            st.write("UPLOADED! " + uploaded_file.name)

    return uploaded_file


def process_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        st.session_state['file_uploaded'] = True
        st.session_state['file_name'] = uploaded_file.name
        bytes_data = uploaded_file.getvalue()
        gdf_plan = gpd.read_file(io.BytesIO(bytes_data))
        gdf_plan.set_crs(epsg=4326, allow_override=True, inplace=True)
        gdf_plan.geometry = gdf_plan.geometry.apply(lambda x: x.buffer(0.001))
        gdf_plan = gdf_plan[gdf_plan.geometry.is_valid]
        return gdf_plan
    else:
        return None


def create_folium_map():
    location = [st.session_state['center']['lat'], st.session_state['center']['lng']]
    m = folium.Map(location=location, zoom_start=11, tiles=None)
    folium.TileLayer('OpenStreetMap', overlay=True, zoom_start=10, max_zoom=22, max_native_zoom=19).add_to(m)
    folium.LayerControl().add_to(m)

    if st.session_state['first_run']:
        Draw(export=False, draw_options={'circle': False, 'polyline': False, 'circlemarker': False}).add_to(m)

    return m

def apply_transformations(feat):
    if feat is not None:
        try:
            # Convert the dictionary directly to a GeoDataFrame
            gdf = gpd.GeoDataFrame.from_features(feat['features'])

            # Apply transformations
            gdf.crs = 'epsg:4326'  # Set CRS to WGS84
            centroid = gdf.dissolve().geometry.centroid.values[0]

            angle = st.sidebar.slider('angle', min_value=0, max_value=360, value=0, step=1)
            x_slide = st.sidebar.slider('x', min_value=-10, max_value=10, value=0, step=1)
            y_slide = st.sidebar.slider('y', min_value=-10, max_value=10, value=0, step=1)
            scale_slide = st.sidebar.slider('scale', min_value=0.5, max_value=1.5, value=1.0, step=0.05)

            gdf.geometry = gdf.geometry.apply(lambda x: rotate(x, angle=angle, origin=centroid))
            gdf.geometry = gdf.geometry.apply(lambda x: translate(x, xoff=x_slide, yoff=y_slide))
            gdf.geometry = gdf.geometry.apply(lambda x: scale(x, xfact=scale_slide, yfact=scale_slide, origin=centroid))
            gdf.to_crs(epsg=4326, inplace=True)

            return gdf.__geo_interface__
        except Exception as e:
            st.error(f"Error applying transformations: {e}")
            return None
    else:
        return None



def mainGeo():
    st.set_option('deprecation.showPyplotGlobalUse', False)
    st.cache_resource(max_entries=10, ttl=3600)

    setup_session_state()
    display_sidebar_info()

    uploaded_file = upload_geojson_file()

    gdf_plan = process_uploaded_file(uploaded_file)

    m = create_folium_map()

    st_data = st_folium(m,
                        key='map5',
                        center=st.session_state["center"],
                        zoom=st.session_state["zoom"],
                        width=700, height=750,
                        feature_group_to_add=st.session_state['fg'])

    click_disable = st_data['last_active_drawing'] is None or not st.session_state['file_uploaded']
    click = st.button('Accept', disabled=click_disable, type="primary")

    if click:
        st.session_state['down_button'] = True
        st.session_state["zoom"] = st_data['zoom']
        st.session_state["center"] = st_data['center']
        st.session_state['feattodownload'] = apply_transformations(st_data['last_active_drawing'])

    if st.session_state['down_button']:
        disabled = False
    else:
        disabled = True

    filename = st.session_state['file_name']
    featcoll = st.session_state['feattodownload']
    geojson = json.dumps(featcoll)

    col1, col2 = st.sidebar.columns(2)

    with col1:
        st.download_button(label=f'{filename[:-8]}_geo.geojson', data=geojson,
                           file_name=f'{filename[:-8]}_geo.geojson', mime='text/json',
                           disabled=disabled, key='download_button', type="primary")

    with col2:
        if st.button(label='Reset Map', key='reset_button', type="primary"):
            st.session_state['feat'] = None
            st.session_state['first_run'] = True
            st.session_state['down_button'] = False
            st.session_state['show_uploaded_legend'] = False
            st.experimental_rerun()


if __name__ == "__main__":
    mainGeo()
