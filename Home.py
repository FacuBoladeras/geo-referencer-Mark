import streamlit as st

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

st.write("# Welcome! 👋")

st.write("This tool is designed to help you convert your floor plans into a format that can be used in your leaflet map.")

st.write("To get started, select a tool from the sidebar.")

st.sidebar.success("Select a tool above.")