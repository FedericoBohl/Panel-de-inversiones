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

colorscale = [
    [0, '#632626'],  # Valor más bajo
    [0.25, '#FF8080'],
    [0.5, '#FFFFFF'],  # Valor medio (0)
    [0.75,'#A5DD9B'],
    [1, '#5F7161']   # Valor más alto
            ]
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

@st.cache_data(show_spinner=False)
def make_acciones(data_now : pd.DataFrame):
    data=pd.read_csv('data_bolsa/bolsa_arg.csv',delimiter=';')
    data_merv=data[data['Merv']==True]
    data_merv=pd.merge(data_now,data_merv,on='simbolo').dropna()
    #data_merv['Var%']=data_merv["Var%"]*100
    data_gen=data[data['Merv']==False]
    data_gen=pd.merge(data_now,data_gen,on='simbolo').dropna()
    #-------------- Fig del Merval  --------------
    df_grouped = data_merv.groupby(["Sector","simbolo"])[["CAP (MM)","Var%","Nombre Completo","ultimoPrecio"]].min().reset_index()
    fig_merv = px.treemap(df_grouped, 
                    path=[px.Constant("Bolsa Argentina"), 'Sector',  'simbolo'],
                    values='CAP (MM)',
                    hover_name="Var%",
                    custom_data=["Nombre Completo",'ultimoPrecio',"Var%"],
                    color='Var%', 
                    range_color =[-6,6],color_continuous_scale=colorscale,
                    labels={'Value': 'Number of Items'},
                    color_continuous_midpoint=0)
    fig_merv.update_traces(marker_line_width = 1.5,marker_line_color='black',
        hovertemplate="<br>".join([
        "<b>Empresa<b>: %{customdata[0]}",
        "<b>Precio (ARS)<b>: %{customdata[1]}"
        ])
        )
    fig_merv.data[0].texttemplate = "<b>%{label}</b><br>%{customdata[2]}%"
    fig_merv.update_traces(marker=dict(cornerradius=10))
    fig_merv.update_layout(margin=dict(l=1, r=1, t=10, b=1))

    #-------------- Fig del General  --------------
    #df_grouped = data_gen.groupby(["Sector","symbol"])[["CAP (MM)","change","Nombre","last"]].min().reset_index()
    #fig_gen = px.treemap(df_grouped, 
    #                path=[px.Constant("Bolsa Argentina"), 'Sector',  'symbol'], #Quite 'Industria', en 3
    #                values='CAP (MM)',
    #                hover_name="change",
    #                custom_data=["Nombre",'last',"change"],
    #                color='change', 
    #                range_color =[-6,6],color_continuous_scale=colorscale,
    #                labels={'Value': 'Number of Items'},
    #                color_continuous_midpoint=0)
    #fig_gen.update_traces(marker_line_width = 1.5,marker_line_color=black,
    #    hovertemplate="<br>".join([
    #    "<b>Empresa<b>: %{customdata[0]}",
    #    "<b>Precio (ARS)<b>: %{customdata[1]}"
    #    ])
    #    )
    #fig_gen.data[0].texttemplate = "<b>%{label}</b><br>%{customdata[2]}%"
    #fig_gen.update_traces(marker=dict(cornerradius=10))
    #fig_gen.update_layout(margin=dict(l=1, r=1, t=10, b=1))
    return fig_merv,None#,fig_gen

@st.cache_data(show_spinner=False)
def load_quotes():
    acciones_now=S.iol.get_quotes('Acciones')
    cedears_now=S.iol.get_quotes('CEDEARs')
    titpub=S.iol.get_quotes('titulosPublicos')
    return acciones_now,cedears_now,titpub

with st.sidebar:
    with st.form('Login',border=False):
        st.text_input('Usuario',key='username')
        st.text_input('Contraseña',key='password',type='password')
        st.form_submit_button('Iniciar Sesion',type='primary')
    try:
        S.iol=load_user_IOL(S.username,S.password)
        S.iol.get_new_token()
    except:pass
st.header('Monitor de Portafolio - :violet[IOL]',divider=True)
#try:
if 'iol' in S:
    if True:#try:
        if (st.button('Recargar Datos')) or (not ('acciones_now' in S)):
            S.acciones_now=S.iol.get_quotes('Acciones')
            S.cedears_now=S.iol.get_quotes('CEDEARs')
            S.titpub=S.iol.get_quotes('titulosPublicos')
            fig,_=make_acciones(data_now=S.acciones_now)
            st.plotly_chart(fig,use_container_width=True)
        #his_op=load_operaciones()
        #st.write(his_op)
        #st.divider()
        #_=calcular_proffit_acciones()
        #st.dataframe(_)
    #except:
    #    pass
else:st.warning('No se ha podido iniciar sesion. Compruebe sus credenciales')

#his_bonos=his_op[his_op['Tipo de Acción']=='Bono']
#his_cedears=his_op[his_op['Tipo de Acción']=='Cedear']

#profit_bonos=pd.DataFrame(index=his_bonos['simbolo'].unique())
#profit_bonos['Cantidad']=0
#profit_bonos['Monto']=0
#profit_bonos['Ganancia']=0
#profit_bonos['Ganancia Real']=0

#profit_cedears=pd.DataFrame(index=his_cedears['simbolo'].unique())
#profit_cedears['Cantidad']=0
#profit_cedears['Monto']=0
#profit_cedears['Ganancia']=0
#profit_cedears['Ganancia Real']=0 

def calcular_proffit_acciones(his_op,_now):
    his_acciones=his_op[his_op['Tipo de Acción']=='Accion']
    profit_acciones=pd.DataFrame(index=his_acciones['Simbolo'].unique())
    profit_acciones['Cantidad']=0
    profit_acciones['Monto']=0
    profit_acciones['Ganancia']=0
    profit_acciones['Ganancia Real']=0
    for i in range(len(his_op.index)):
        row=his_op.iloc[i]
        st.write(row['Simbolo'])
        if row['Tipo Transacción']=='Compra':
            profit_acciones.at[row['Simbolo'],'Cantidad']+=row['Cantidad']
            profit_acciones.at[row['Simbolo'],'Monto']+=(row['Cantidad']*row['Precio Ponderado'])
            profit_acciones.at[row['Simbolo'],'Ganancia']+=(row['Cantidad']*(_now_.loc[row['Simbolo'],'ultimoPrecio']/row['Precio Ponderado']))
        else:
            profit_acciones.at[row['Simbolo'],'Cantidad']-=row['Cantidad']
            profit_acciones.at[row['Simbolo'],'Monto']-=(row['Cantidad']*row['Precio Ponderado'])
            profit_acciones.at[row['Simbolo'],'Ganancia']+=(row['Cantidad']*(_now_.loc[row['Simbolo'],'ultimoPrecio']/row['Precio Ponderado']))
        return profit_acciones

S.acciones_now=S.iol.get_quotes('Acciones')
his_op=load_operaciones()
for i in range(len(his_op.index)):
    st.write(his_op.iloc[i]['Simbolo'])
st.divider()
_now_=S.acciones_now.copy()
_now_.set_index('simbolo',inplace=True)
st.write(calcular_proffit_acciones(his_op,_now_))

