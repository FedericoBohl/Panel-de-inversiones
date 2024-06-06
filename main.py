import streamlit as st
from streamlit import session_state as S
from plotly.subplots import make_subplots
import plotly.io as pio
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import openpyxl

from IOL import TokenManager

def load_operaciones(path='Operaciones.xlsx'):
    df=pd.read_excel(path)
    st.write(df)

@st.cache_data(show_spinner=False)
def load_user_IOL(username,password):
    token_manager = TokenManager(username,password)
    return token_manager

st.sidebar.text_input('Usuario',key='username')
st.sidebar.text_input('Contraseña',key='password',type='password')
st.header('Monitor de Portafolio - :violet[IOL]',divider=True)
load_operaciones()
try:
    iol=load_user_IOL(S.username,S.password)
    if (st.button('Recargar Datos')) or not ('_datosiol_' in S):
        S.acciones_now=iol.get_quotes('Acciones','argentina')
        S.cedears_now=iol.get_quotes('CEDEARs','argentina')
        S.titpub=iol.get_quotes('titulosPublicos','argentina')
    st.dataframe(S.acciones_now)
    st.divider()
    load_operaciones()
except:pass