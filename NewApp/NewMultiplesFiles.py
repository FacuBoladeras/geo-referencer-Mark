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
import seaborn as sns

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
    list_index = 0
    layer_attr_val = ['71-spaces_data', '003-Room_number_text','Workplaces']
    gdf_points = gdf[gdf['Layer'].isin(layer_attr_val)]

    if not gdf_points.empty:
        if gdf_points['Layer'].iloc[0] == '71-spaces_data':
            list_index = 1

 
        gdf_points = gdf_points[gdf_points['geometry'].geom_type == 'Point']


    text_prop = []
    for i, item in gdf_pol.iterrows():
        gdf_inter = gdf_points.overlay(gdf_pol.loc[[i]], how='intersection')
        prop = gdf_inter['Text'].to_list()
        if prop and len(prop[0].split('\n')) > 1:
            prop = [prop[0].split('\n')[0]]
        text_prop.append(prop)

    gdf_pol['prop'] = text_prop
    featcoll = gdf_pol.__geo_interface__

    type_prop = "area.space"
    custom_prop = "[object Object]"
    for i, feat in enumerate(featcoll['features']):
        try:
            spaceid = feat['properties']['prop'][list_index]
        except:
            spaceid = None
        feat['id'] = spaceid
        feat['properties'] = {
            "Layer": gdf['Layer'].iloc[i],
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


# list with possible values for 'layer' column

layer_val = ['70-spaces', 'A-ROOMS','A-Areas','Workplaces','_MKD_ROOM']

def mainFiles():
    st.set_option('deprecation.showPyplotGlobalUse', False)
    st.sidebar.title("📂 Convert multiple files")
    st.sidebar.markdown("**Upload multiple files at once and convert them to GeoJSON**")
    st.markdown("### Conversion Tool")
    info = """
This tool allows you to upload multiple DWG/DFX files and then download them in GeoJSON format. 
For those files that do not contain the geometries in the default layer, it is possible to select the corresponding layer before generating the conversion and download.
"""

    st.sidebar.markdown(info)

    uploaded_files = st.file_uploader("Choose DWG or DXF files", accept_multiple_files=True, type=['dxf', 'dwg'], key="1")

    if uploaded_files is not None:
        total_files = len(uploaded_files)
        for i, file in enumerate(uploaded_files):
            progress_bar = st.progress((i + 1) / total_files)
            try:
                if file.name.endswith('.dxf') or file.name.endswith('.DXF'):
                    gdf, file_name = dxf_to_gdf(file)
                elif file.name.endswith('.dwg') or file.name.endswith('.DWG'):
                    gdf, file_name = dwg_to_gdf(file)

                # gdf_spaces = gdf[gdf['Layer'].isin(layer_val)]

                # if not gdf_spaces.empty:
                #     gdf_pol = gpd.GeoSeries(polygonize(gdf_spaces.geometry))
                #     gdf_pol = gpd.GeoDataFrame(gdf_pol, columns=['geometry'])
                # else:
                st.warning("Select area layers...")
                gdf_spaces = select_and_visualize_layers(gdf)
                gdf_pol = gpd.GeoSeries(polygonize(gdf_spaces.geometry))
                gdf_pol = gpd.GeoDataFrame(gdf_pol, columns=['geometry'])

                sns.set_theme(style="whitegrid")
                fig, ax = plt.subplots()
                fig.patch.set_facecolor('#EFC9AF')  # Set figure background color
                ax.set_facecolor('#EFC9AF')  # Set axes background color

                gdf_pol.plot(ax=ax, color='#1F8AC0', alpha=1.0, edgecolor='k', linewidth=0.5)
                plt.axis('off')
                st.pyplot(fig)

                geojson, geojson_filename = process_properties(gdf_pol, gdf, file_name)

                download_button_key = f"download_button_{i}"
                st.download_button('Download GeoJson', geojson, mime='text/json', file_name=geojson_filename, key=download_button_key, type="primary")

            except IndexError as e:
                st.warning("There was an error trying to access the layer")
                print(e)
            finally:
                progress_bar.empty()

if __name__ == "__main__":
    mainFiles()
