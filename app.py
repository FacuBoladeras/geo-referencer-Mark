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
    page_title="Floor Plan Conversion Tool",
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
def dxf_to_gdf(file):
    file_name = file.name
    bytes_data = file.getvalue()
    with MemoryFile(bytes_data) as memfile:
        with memfile.open() as src:
            df1 = pd.DataFrame(src)
            # Check Geometry
            def isvalid(geom):
                try:
                    shape(geom)
                    return 1
                except:
                    return 0
            df1['isvalid'] = df1['geometry'].apply(
                lambda x: isvalid(x))
            df1 = df1[df1['isvalid'] == 1]
            
            collection = json.loads(df1.to_json(orient='records'))
            
            gdf = gpd.GeoDataFrame.from_features(collection)
            return gdf , file_name

# declare state variables

if 'fg' not in st.session_state:
    st.session_state['fg'] = folium.FeatureGroup(name="Markers",)

if 'feat' not in st.session_state:
    st.session_state['feat'] = None 

if 'first_run' not in st.session_state:
    st.session_state['first_run'] = True

if 'center' not in st.session_state:
    st.session_state['center'] = {'lat': 52.156046, 'lng': 5.587156}

if 'zoom' not in st.session_state:
    st.session_state['zoom'] = 13

if 'file_uploaded' not in st.session_state:
    st.session_state['file_uploaded'] = False

if 'down_button' not in st.session_state:
    st.session_state['down_button'] = False

if 'feattodownload' not in st.session_state:
    st.session_state['feattodownload'] = None

st.title("Conversion Tool")


tab3 ,tab1, tab2 = st.tabs(["Geo Reference","Multiple Files", "Select layer"])

with tab1:
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

with tab2:
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

with tab3:
    st.info("Allow to project to geographic coordinates the GeoJSON file.")
    uploaded_file = st.file_uploader(
    "Choose a GeoJSON file", accept_multiple_files=False, type="geojson", key="3")
    fig, ax = plt.subplots()
    if uploaded_file is not None:
        with st.spinner('Uploading files ...'):
            # convert uploaded file to geodataframe
            st.session_state['file_uploaded'] = True
            bytes_data = uploaded_file.getvalue()
            filename = uploaded_file.name
            gdf_plan = gpd.read_file(io.BytesIO(bytes_data))
            gdf_plan.set_crs(epsg=4326,allow_override=True, inplace=True)
            # fix non valid polygons
            gdf_plan.geometry = gdf_plan.geometry.apply(lambda x: x.buffer(0.001))
            gdf_plan = gdf_plan[gdf_plan.geometry.is_valid]

            # gdf_plot = gdf_plan.set_crs(epsg=3857,allow_override=True)
            # ax = gdf_plot.plot(ax=ax, color='blue', alpha=0.5,
            #                 edgecolor='k', linewidth=0.5)
            # plt.axis('off')
            # st.pyplot(aspect=1)

    # Map
    feat = st.session_state['feat']
    location = [st.session_state['center']['lat'], st.session_state['center']['lng']]
    m = folium.Map(location=location, zoom_start=16, tiles=None)
    fg = folium.FeatureGroup(name="draw",)
    folium.TileLayer('OpenStreetMap',overlay=True, zoom_start=12, max_zoom=22,max_native_zoom=19).add_to(m)
    folium.LayerControl().add_to(m)
    if st.session_state['first_run']:
        Draw(export=False,draw_options={'circle':False,'polyline':False,'circlemarker':False}).add_to(m)

    angle = st.sidebar.slider('angle', min_value=0, max_value=180, value=0, step=1)
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
        print('scale:', scale)

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
            print('first run')
            st.session_state['first_run'] = False
            st.experimental_rerun()


    # Download button
    if st.session_state['down_button']:
        featcoll = st.session_state['feattodownload']
        geojson = json.dumps(featcoll)

        st.sidebar.download_button(label=f'{filename[:-8]}_geo.geojson', data=geojson ,file_name=f'{filename[:-8]}_geo.geojson', mime='text/json', key='down_button')


