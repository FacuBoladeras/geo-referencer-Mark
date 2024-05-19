import warnings
warnings.filterwarnings("ignore")
import streamlit as st
import json
import pandas as pd
import geopandas as gpd
from shapely.ops import polygonize
import os
from fiona.io import MemoryFile
import matplotlib.pyplot as plt
from .FuncionCapas import select_and_visualize_layers
import cloudconvert
import dotenv

import tempfile
temp_dir = tempfile.gettempdir()

# Load environment variables
dotenv.load_dotenv()

api_key = os.getenv('API_KEY')
cloudconvert.configure(api_key=api_key, sandbox=False)

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
        
@st.cache_data
def dwg_to_gdf(file):
    # cloud convert job definition
    jobdef = {
            "tasks": {
                "import-1": {
                    "operation": "import/upload"
                },
                "convert-1": {
                    "operation": "convert",
                    "input_format": "dwg",
                    "output_format": "dxf",
                    "engine": "cadconverter",
                    "input": [
                        "import-1"
                    ],
                    "filename": "output.dxf"
                },
                "export-1": {
                    "operation": "export/url",
                    "input": [
                        "convert-1"
                    ],
                    "inline": False,
                    "archive_multiple_files": False
                }
            },
            "tag": "jobbuilder"
        }
    # create job
    job = cloudconvert.Job.create(payload=jobdef)
    # get upload task id
    upload_task_id = job['tasks'][0]['id']
    upload_task = cloudconvert.Task.find(id=upload_task_id)

    file_name = file.name
    bytes_data = file.getvalue()

    # save dwg file in temp directory
    path = os.path.join(temp_dir, 'temp.dwg')
    with open(path, 'wb') as f:
        f.write(bytes_data)
    # upload file to cloudconvert
    res = cloudconvert.Task.upload(path, task=upload_task)

    # get the export task id
    exported_url_task_id = job['tasks'][2]['id']
    res = cloudconvert.Task.wait(id=exported_url_task_id)  # Wait for job completion
    file = res.get("result").get("files")[0]
    path_out = os.path.join(temp_dir, file['filename'])
    # download the file to the temp directory
    res = cloudconvert.download(filename=path_out, url=file['url'])
    # read the file
    with open(path_out, 'rb') as f:
        content = f.read()
        with MemoryFile(content) as memfile:
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

    uploaded_files = st.file_uploader("Choose DWG or DXF files", accept_multiple_files=True, type=['dxf','dwg'], key="1")

    if uploaded_files is not None:
        total_files = len(uploaded_files)
        for i, file in enumerate(uploaded_files):
            progress_bar = st.progress((i + 1) / total_files)
            try:
                if file.name.endswith('.dxf') or file.name.endswith('.DXF'):
                    gdf, file_name = dxf_to_gdf(file)
                elif file.name.endswith('.dwg') or file.name.endswith('.DWG'):
                    gdf, file_name = dwg_to_gdf(file)

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
