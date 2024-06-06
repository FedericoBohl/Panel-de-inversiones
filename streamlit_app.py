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
st.set_page_config(
    page_title="Portafolio IOL",
    page_icon="logo.jpg",
    layout="wide",
    initial_sidebar_state="expanded")

def load_operaciones(path='Operaciones.xlsx'):
    df=pd.read_excel(path)
    return df.sort_values(by='Fecha Liquidación', ascending=True)

@st.cache_data(show_spinner=False)
def load_user_IOL(username,password):
    token_manager = TokenManager(username,password)
    return token_manager

def calcular_proffit_acciones():
    his_acciones=his_op[his_op['Tipo de Acción']=='Accion']
    profit_acciones=pd.DataFrame(index=his_acciones['Simbolo'].unique())
    profit_acciones['Cantidad']=0
    profit_acciones['Monto']=0
    profit_acciones['Ganancia']=0
    profit_acciones['Ganancia Real']=0
    for i in range(len(his_acciones.index)):
        row=his_op.iloc[i]
        if row['Tipo Transacción']=='Compra':
            profit_acciones.at[row['Simbolo'],'Cantidad']+=row['Cantidad']
            profit_acciones.at[row['Simbolo'],'Monto']+=(row['Cantidad']*row['Precio Ponderado'])
            profit_acciones.at[row['Simbolo'],'Ganancia']+=(row['Cantidad']*(S.acciones_now.iloc[row['Simbolo']['ultimoPrecio']]/row['Precio Ponderado']))
        else:
            profit_acciones.at[row['Simbolo'],'Cantidad']-=row['Cantidad']
            profit_acciones.at[row['Simbolo'],'Monto']-=(row['Cantidad']*row['Precio Ponderado'])
            profit_acciones.at[row['Simbolo'],'Ganancia']+=(row['Cantidad']*(S.acciones_now.iloc[row['Simbolo']['ultimoPrecio']]/row['Precio Ponderado']))
        return profit_acciones
with st.sidebar:
    with st.form('Login',border=False):
        st.text_input('Usuario',key='username')
        st.text_input('Contraseña',key='password',type='password')
        st.form_submit_button('Iniciar Sesion',type='primary')
    try:
        S.iol=load_user_IOL(S.username,S.password)
        S.iol.get_new_token()
    except:pass
st.write(S.iol)
st.header('Monitor de Portafolio - :violet[IOL]',divider=True)
#try:
if 'iol' in S:
    try:
        if (not ('acciones_now' in S)) or (st.button('Recargar Datos')):
            S.acciones_now=S.iol.get_quotes('Acciones','argentina')
            S.cedears_now=S.iol.get_quotes('CEDEARs','argentina')
            S.titpub=S.iol.get_quotes('titulosPublicos','argentina')
        st.dataframe(S.acciones_now)
        his_op=load_operaciones()
        st.write(his_op)
        st.divider()
        _=calcular_proffit_acciones()
        st.dataframe(_)
    except:pass
else:st.warning('No se ha podido iniciar sesion. Compruebe sus credenciales')

#his_bonos=his_op[his_op['Tipo de Acción']=='Bono']
#his_cedears=his_op[his_op['Tipo de Acción']=='Cedear']

#profit_bonos=pd.DataFrame(index=his_bonos['Simbolo'].unique())
#profit_bonos['Cantidad']=0
#profit_bonos['Monto']=0
#profit_bonos['Ganancia']=0
#profit_bonos['Ganancia Real']=0

#profit_cedears=pd.DataFrame(index=his_cedears['Simbolo'].unique())
#profit_cedears['Cantidad']=0
#profit_cedears['Monto']=0
#profit_cedears['Ganancia']=0
#profit_cedears['Ganancia Real']=0

