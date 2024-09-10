import streamlit as st
from streamlit import session_state as S
from plotly.subplots import make_subplots
import plotly.io as pio
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import openpyxl
from datetime import datetime
import yfinance as yf
import requests
from bs4 import BeautifulSoup

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
def load_user_IOL(username,password)->TokenManager:
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

@st.cache_data(show_spinner=False)
def calcular_proffit_acciones(his_op,_now):
    his_acciones=his_op[his_op['Tipo de Acción']=='Accion']
    profit_acciones=pd.DataFrame(index=his_acciones['Simbolo'].unique())
    profit_acciones['Cantidad']=0
    profit_acciones['Monto']=0
    profit_acciones['Ganancia']=0
    profit_acciones['Ganancia%']=[[] for _ in range(len(profit_acciones))]
    #profit_acciones['Ganancia Real']=0
    for i in range(len(his_acciones.index)):
        row=his_acciones.iloc[i]
        if row['Tipo Transacción']=='Compra':
            profit_acciones.at[row['Simbolo'],'Cantidad']+=row['Cantidad']
            profit_acciones.at[row['Simbolo'],'Ganancia']+=(row['Cantidad']*(_now_.loc[row['Simbolo'],'ultimoPrecio']-row['Precio Ponderado']))
            profit_acciones.at[row['Simbolo'],'Ganancia%'].append(
                            row['Cantidad']*(_now_.loc[row['Simbolo'],'ultimoPrecio']/row['Precio Ponderado'] -1)/(datetime.now()-row['Fecha Liquidación']).days
                                                                  )
        else:
            profit_acciones.at[row['Simbolo'],'Cantidad']-=row['Cantidad']
            #profit_acciones.at[row['Simbolo'],'Ganancia']+=(row['Cantidad']*(_now_.loc[row['Simbolo'],'ultimoPrecio']-row['Precio Ponderado']))
    for i in range(len(profit_acciones.index)):
        if profit_acciones.iloc[i]['Cantidad'] != 0:
            profit_acciones.at[profit_acciones.index[i], 'Ganancia%'] = 100*sum(profit_acciones.at[profit_acciones.index[i], 'Ganancia%']) / profit_acciones.at[profit_acciones.index[i], 'Cantidad']
        else:
            profit_acciones.at[profit_acciones.index[i], 'Ganancia%'] = None
    montos=[S.port[S.port['simbolo']==i].values.tolist()[0][1] for i in profit_acciones.index]
    profit_acciones['Monto']=montos
    return profit_acciones.dropna().sort_values(by='Ganancia%', ascending=True)

@st.cache_data(show_spinner=False)
def calcular_proffit_cedears(his_op,_now):
    his_acciones=his_op[his_op['Tipo de Acción']=='Cedear']
    ratios={'JPM':3,
            'AAPL':2,
            'MELI':2,
            'VIST':3}
    fecha_limite = pd.Timestamp('2024-01-26')
    for ticker in ratios.keys():
        filtro = (his_acciones['Simbolo'] == ticker) & (his_acciones['Fecha Liquidación'] < fecha_limite)
        his_acciones.loc[filtro, 'Cantidad'] *= ratios[ticker]
        his_acciones.loc[filtro, 'Precio Ponderado'] /= ratios[ticker]
    
    profit_acciones=pd.DataFrame(index=his_acciones['Simbolo'].unique())
    profit_acciones['Cantidad']=0
    profit_acciones['Monto']=0
    profit_acciones['Ganancia']=0
    profit_acciones['Ganancia%']=[[] for _ in range(len(profit_acciones))]
    #profit_acciones['Ganancia Real']=0
    for i in range(len(his_acciones.index)):
        row=his_acciones.iloc[i]
        if row['Tipo Transacción']=='Compra':
            profit_acciones.at[row['Simbolo'],'Cantidad']+=row['Cantidad']
            profit_acciones.at[row['Simbolo'],'Ganancia']+=(row['Cantidad']*(_now_.loc[row['Simbolo'],'ultimoPrecio']-row['Precio Ponderado']))
            profit_acciones.at[row['Simbolo'],'Ganancia%'].append(
                            row['Cantidad']*(_now_.loc[row['Simbolo'],'ultimoPrecio']/row['Precio Ponderado'] -1)/(datetime.now()-row['Fecha Liquidación']).days
                                                                  )
        else:
            profit_acciones.at[row['Simbolo'],'Cantidad']-=row['Cantidad']
            #profit_acciones.at[row['Simbolo'],'Ganancia']+=(row['Cantidad']*(_now_.loc[row['Simbolo'],'ultimoPrecio']-row['Precio Ponderado']))
    for i in range(len(profit_acciones.index)):
        if profit_acciones.iloc[i]['Cantidad'] != 0:
            profit_acciones.at[profit_acciones.index[i], 'Ganancia%'] = 100*sum(profit_acciones.at[profit_acciones.index[i], 'Ganancia%']) / profit_acciones.at[profit_acciones.index[i], 'Cantidad']
        else:
            profit_acciones.at[profit_acciones.index[i], 'Ganancia%'] = None
    profit_acciones=profit_acciones.dropna().sort_values(by='Ganancia%', ascending=True)
    montos=[S.port[S.port['simbolo']==i].values.tolist()[0][1] for i in profit_acciones.index]
    profit_acciones['Monto']=montos
    return profit_acciones.dropna().sort_values(by='Ganancia%', ascending=True)

@st.cache_data(show_spinner=False)
def calcular_proffit_bonos(his_op,_now_):
    his_acciones=his_op[his_op['Tipo de Acción']=='Bono']
    his_acciones['Precio Ponderado']=his_acciones['Precio Ponderado']/100
    _now_['ultimoPrecio']=_now_['ultimoPrecio']/100
    profit_acciones=pd.DataFrame(index=his_acciones['Simbolo'].unique())
    profit_acciones['Cantidad']=0
    profit_acciones['Monto']=0
    profit_acciones['Ganancia']=0
    profit_acciones['Ganancia%']=[[] for _ in range(len(profit_acciones))]
    for i in range(len(his_acciones.index)):
        row=his_acciones.iloc[i]
        if row['Tipo Transacción']=='Compra':
            profit_acciones.at[row['Simbolo'],'Cantidad']+=row['Cantidad']
            profit_acciones.at[row['Simbolo'],'Ganancia']+=(row['Cantidad']*(_now_.loc[row['Simbolo'],'ultimoPrecio']-row['Precio Ponderado']))
            profit_acciones.at[row['Simbolo'],'Ganancia%'].append(
                            row['Cantidad']*(_now_.loc[row['Simbolo'],'ultimoPrecio']/row['Precio Ponderado'] -1)/(datetime.now()-row['Fecha Liquidación']).days
                                                                  )
        else:
            profit_acciones.at[row['Simbolo'],'Cantidad']-=row['Cantidad']
            #profit_acciones.at[row['Simbolo'],'Ganancia']+=(row['Cantidad']*(_now_.loc[row['Simbolo'],'ultimoPrecio']-row['Precio Ponderado']))
    for i in range(len(profit_acciones.index)):
        if profit_acciones.iloc[i]['Cantidad'] != 0:
            profit_acciones.at[profit_acciones.index[i], 'Ganancia%'] = 100*sum(profit_acciones.at[profit_acciones.index[i], 'Ganancia%']) / profit_acciones.at[profit_acciones.index[i], 'Cantidad']
        else:
            profit_acciones.at[profit_acciones.index[i], 'Ganancia%'] = None
    profit_acciones=profit_acciones.dropna().sort_values(by='Ganancia%', ascending=True)
    montos=[]
    for i in profit_acciones.index:
        montos.append(S.port[S.port['simbolo']==i]['valorizado'].sum())
    profit_acciones['Monto']=montos
    return profit_acciones[profit_acciones['Cantidad']>0]

@st.cache_data(show_spinner=False)
def rendimiento_portfolio(now):
    op_hist=S.iol.get_operaciones_hist()
    op_hist=op_hist.copy()
    ratios={'JPM':3,
            'AAPL':2,
            'MELI':2,
            'VIST':3}
    fecha_limite = pd.Timestamp('2024-01-26')
    for ticker in ratios.keys():
        filtro = (op_hist['simbolo'] == ticker) & (op_hist['fechaOperada'] < fecha_limite)
        op_hist.loc[filtro, 'cantidadOperada'] *= ratios[ticker]
    tickers={
        'YPFD':'YPF',
        'PAMP':'PAM',
        "BRKB":'BRK-B',
        'TGSU2':'TGS',
        'TECO2':'TEO',
        'AE38':'AE38D',
        'AL29':'AL29D',
        'AL30':'AL30D',
        'AL35':'AL35D',
        'AL41':'AL41D',
        'CO26':'CO26D',
        'GD29':'GD29D',
        'GD30':'GD30D',
        'GD35':'GD35D',
        'GD38':'GD38D',
        'GD41':'GD41D',
        'GD46':'GD46D',
        'T2X5':'T2X5D',
        'T4X4':'T4X4D',
        'TX26':'TX26D',
        'TX28':'TX28D',
        'BPOA7':'BPA7D',
        'BPOB7':'BPB7D',
        'BPOC7':'BPC7D',
        'BPOD7':'BPD7D',
        'BPJ25':'BPJ5D',
        'BPY26':'BPY6D'
    }

    tickers_usd={}
    vars_usd={}
    fails=[]
    uniques=op_hist['simbolo'].unique()
    for ticker in uniques:
        try:
            data = yf.download(ticker if ticker not in tickers.keys() else tickers[ticker], start="2023-01-01", end=pd.Timestamp.today().strftime('%Y-%m-%d'), interval="1d")
            precios_mensuales = data['Adj Close'].resample('M').last()
            tickers_usd[ticker]=precios_mensuales
            open_=data['Open'].resample('M').first()
            close_=data['Close'].resample('M').last()
            vars_usd[ticker]=close_/open_-1
        except:
            fails.append(ticker)
            continue
    op_hist['fechaOperada']=[x.strftime('%Y-%m')for x in op_hist['fechaOperada']]
    op_hist['cantidadOperada']=[op_hist.loc[x]['cantidadOperada'] if op_hist.loc[x]['tipo']=='Compra' else -op_hist.loc[x]['cantidadOperada'] for x in op_hist.index]
    op_hist=op_hist.groupby(by=['fechaOperada','simbolo'])[['cantidadOperada']].sum()
    df = pd.DataFrame(index=pd.date_range(start="2023-01-01", end=pd.Timestamp.today(), freq='M'), columns=[s for s in uniques])
    df.index=[x.strftime('%Y-%m') for x in df.index]
    df=df.loc[op_hist.index[0][0]:]
    for ind in op_hist.index:
        df.at[ind[0],ind[1]]=op_hist.loc[ind][['cantidadOperada']].sum()
    df_acum={}
    for col in df.columns:
        acumulado = 0
        valores_acumulados=[]
        # Iterar sobre la lista
        for valor in df[col]:
            if not np.isnan(valor):
                acumulado += valor
            # Agregar el valor acumulado actual a la lista
            valores_acumulados.append(acumulado)
        df_acum[col]=valores_acumulados
    df_acum=pd.DataFrame(df_acum,index=df.index)
    response=requests.get('https://marcosemmi.com/ratios-de-cedears/')
    soup=BeautifulSoup(response.text,'html.parser')
    table=soup.find('table')
    rows = []
    for tr in table.find_all('tr'):
        cells = tr.find_all('td')
        row = [cell.get_text(strip=True) for cell in cells]
        if row:  # Ignorar filas vacías
            rows.append(row)
    ratios=pd.DataFrame(rows,columns=['ticker','nombre','cod bolsa','ratio','ticker-usd','area'])
    ratios['ratio']=[float(x.split(':')[0]) for x in ratios['ratio']]
    ratios.set_index('ticker',inplace=True)
    ratios=ratios['ratio']
    cantXaccion = {
        'PAMP': 25,
        'YPFD': 1,
        'GGAL': 10,
        'CEPU': 10,
        'COME': 1,
        'TGSU2': 5,
        'CRES': 10,
        'EDN': 20,
        'LOMA': 5,
        'BMA': 10,
        'BBAR': 3,
        'SUPV': 5,
        'IRSA': 10,
        'TECO2': 5,
        'TS': 2,
        'IRCP': 4,
        'SPY': 20,
        'QQQ':20,
        'DIA':20,
        'IWM':10
    }
    price_usd=pd.DataFrame(tickers_usd)
    price_usd.index=[x.strftime('%Y-%m') for x in price_usd.index]
    price_usd=price_usd.loc[op_hist.index[0][0]:]
    for col in price_usd.columns:
        if col in cantXaccion.keys():
            price_usd[col]=price_usd[col]/cantXaccion[col]
        elif col in ratios.index:
            price_usd[col]=price_usd[col]/ratios[col]
    df_val=df_acum.copy()[price_usd.columns]  #CUANDO CONSIGA DATOS DE BONOS DEBERÍA IR "df.columns"
    for col in df_val.columns:
        for ind in df_val.index:
            df_val.at[ind,col]=df_acum.at[ind,col]*price_usd.at[ind,col]
    df_val['Portfolio']=[sum(df_val.loc[x]) for x in df_val.index]
    vars_usd=pd.DataFrame(vars_usd)
    vars_usd.index=[x.strftime('%Y-%m') for x in vars_usd.index]
    vars_usd=vars_usd.loc[op_hist.index[0][0]:]
    spy=vars_usd['SPY']
    var_pond=df_val.copy()
    for col in var_pond.columns:
        var_pond[col]=var_pond[col]/var_pond['Portfolio']
    var_pond=var_pond.drop(columns=['Portfolio'])
    for ind in var_pond.index:
        for col in var_pond.columns:
            var_pond.at[ind,col]*=vars_usd.at[ind,col]
    var_pond['Portfolio']=[sum(var_pond.loc[x]) for x in var_pond.index]

    fig=make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=df_val.index,y=df_val['Portfolio'],name='Portfolio',marker_color='goldenrod'),secondary_y=False)
    fig.add_trace(go.Scatter(x=spy.index,y=spy*100,name='SPY',marker_color='lightslategrey'),secondary_y=True)
    fig.add_trace(go.Scatter(x=var_pond.index,y=var_pond['Portfolio']*100,name='Rendimiento Portfolio',marker_color='crimson',fill='tonexty',fillcolor='lightgreen'),secondary_y=True)
    fig.update_layout(hovermode="x unified", margin=dict(l=1, r=1, t=25, b=1),height=450,bargap=0.2,legend=dict(
                                        orientation="h",
                                        yanchor="bottom",
                                        y=-0.2,
                                        xanchor="center",
                                        x=0.5,
                                        bordercolor='black',
                                        borderwidth=2
                                    ),
                                    yaxis=dict(title="USD",showgrid=False, zeroline=False, showline=True),
                                    yaxis2=dict(title='Var. Mensual', side='right',showgrid=True, zeroline=True, showline=True,ticksuffix="%"),
                                    title={
                                    'text': "Rendimiento de las acciones Argentinas y Extranjeras",
                                    'y':-0.2,
                                    'x':0.5,
                                    'xanchor': 'center',
                                    'yanchor': 'top'}
                                    )
    st.plotly_chart(fig,config={'displayModeBar': False},use_container_width=True)





with st.sidebar:
    with st.form('Login',border=False):
        st.text_input('Usuario',key='username')
        st.text_input('Contraseña',key='password',type='password')
        st.form_submit_button('Iniciar Sesion',type='primary')
    try:
        S.iol:TokenManager=load_user_IOL(S.username,S.password)
        S.iol.get_new_token()
        st.write(S.iol.token_info)
    except:pass
st.header('Monitor de Portafolio - :violet[IOL]',divider=True)
#try:
if 'iol' in S:
    if True:#try:
        if (st.button('Recargar Datos')) or (not ('acciones_now' in S)):
            S.acciones_now=S.iol.get_quotes('Acciones')
            S.cedears_now=S.iol.get_quotes('CEDEARs')
            S.titpub=S.iol.get_quotes('titulosPublicos')
            S.port=S.iol.get_portfolio()
            S.operaciones=S.iol.get_operaciones(S.acciones_now,S.cedears_now,S.titpub)
        t_total,t_acc,t_ced,t_bon=st.tabs(['Total Portafolio','Acciones Argentinas','Cedears','Títulos Públicos'])
        with t_total:
            c1,c2=st.columns((0.4,0.6))
            fig = px.sunburst(S.port, path=['tipo', 'simbolo'],
                       values=S.port['valorizado%'],custom_data=["valorizado",'variacionDiaria'])
            fig.update_traces(
            hovertemplate="<br>".join([
            "<b><b>%{label}",
            "<b>Valorizado<b>: %{customdata[0]} (%{value}%)",
            "<b>Variación<b>: %{customdata[1]}%"
            ])
            )
            fig.update_layout(margin=dict(l=1, r=1, t=75, b=1),height=600)
            c1.plotly_chart(fig,use_container_width=True)
            with c2:
                _=round(S.port['gananciaDiariaPonderada'].sum(),2)
                col=f':green[{_}%]' if _>0 else (f':red[{_}%]' if _<0 else f':gray[{_}%]')
                st.header(f"Ganancia de hoy: {col}")
                c21,c22=st.columns(2)
                ganancia_diaria_por_tipo = S.port.groupby('tipo')['gananciaDiariaPonderada'].sum().tolist()#.reset_index()
                fig=go.Figure()
                fig.add_trace(go.Indicator(mode='delta',value=ganancia_diaria_por_tipo[0],
                                           delta = {"reference": 0, "valueformat": ".3f",'suffix':'%'},title = {"text": "Acciones"},
                                           domain = {'row': 0, 'column': 0}
                                           ))
                fig.add_trace(go.Indicator(mode='delta',value=ganancia_diaria_por_tipo[2],
                                           delta = {"reference": 0, "valueformat": ".3f",'suffix':'%'},title = {"text": "Cedears"},
                                           domain = {'row': 0, 'column': 1}
                                           ))
                fig.add_trace(go.Indicator(mode='delta',value=ganancia_diaria_por_tipo[1],
                                           delta = {"reference": 0, "valueformat": ".3f",'suffix':'%'},title = {"text": "Bonos"},
                                           domain = {'row': 0, 'column': 2}
                                           ))
                fig.update_layout(grid = {'rows': 1, 'columns': 3, 'pattern': "independent"})
                fig.update_layout(margin=dict(l=1, r=1, t=1, b=1))
                st.plotly_chart(fig,use_container_width=True)
                c21.subheader(':green[Top Winners]')
                for i in S.port.nlargest(3, 'variacionDiaria').values.tolist():
                    c21.caption(f"* {i[2]}:  {i[0]}%")
                c22.subheader(':red[Top Losers]')
                for i in S.port.nsmallest(3, 'variacionDiaria').values.tolist():
                    c22.caption(f"* {i[2]}:  {i[0]}%")
            
            rendimiento_portfolio(datetime.now().strftime("%Y-%m-%d"))
        with t_acc:
            fig,_=make_acciones(data_now=S.acciones_now)
            st.plotly_chart(fig,use_container_width=True)
            _now_=S.acciones_now.copy()
            _now_.set_index('simbolo',inplace=True)
            prof_acc=calcular_proffit_acciones(S.operaciones,_now_)
            c1,c2=st.columns(2)
            fig=go.Figure()
            fig.add_trace(go.Bar(x=prof_acc['Ganancia%'],y=prof_acc.index,orientation='h',marker_color='#683CFC'))
            fig.update_layout(margin=dict(l=1, r=1, t=1, b=1))
            with c1.container(border=True):
                c11,c12=st.columns(2)
                val=0
                proff_av=0
                tot_ced=sum(prof_acc['Cantidad'])
                for i in range(len(prof_acc)):
                    val+=(prof_acc.iloc[i]['Cantidad']*_now_.loc[prof_acc.index[i],'ultimoPrecio'])
                    proff_av+=(prof_acc.iloc[i]['Ganancia%']*prof_acc.iloc[i]['Cantidad']/tot_ced)
                c11.metric('Total valuado',val)
                c12.metric('Ganancia Diaria Promedio',f'{round(proff_av,2)}%')

            c1.dataframe(prof_acc.drop(columns=['Ganancia%']),use_container_width=True)
            c2.subheader('Ganancia diaria promedio')
            c2.plotly_chart(fig,use_container_width=True)
        with t_ced:
            _now_=S.cedears_now.copy()
            _now_.set_index('simbolo',inplace=True)
            prof_ced=calcular_proffit_cedears(S.operaciones,_now_)
            c1,c2=st.columns(2)
            fig=go.Figure()
            fig.add_trace(go.Bar(x=prof_ced['Ganancia%'],y=prof_ced.index,orientation='h',marker_color='#683CFC'))
            fig.update_layout(margin=dict(l=1, r=1, t=1, b=1))
            with c1.container(border=True):
                c11,c12=st.columns(2)
                val=0
                proff_av=0
                tot_ced=sum(prof_ced['Cantidad'])
                for i in range(len(prof_ced)):
                    val+=(prof_ced.iloc[i]['Cantidad']*_now_.loc[prof_ced.index[i],'ultimoPrecio'])
                    proff_av+=(prof_ced.iloc[i]['Ganancia%']*prof_ced.iloc[i]['Cantidad']/tot_ced)
                c11.metric('Total valuado',val)
                c12.metric('Ganancia Diaria Promedio',f'{round(proff_av,2)}%')
            c1.dataframe(prof_ced.drop(columns=['Ganancia%']),use_container_width=True)
            c2.subheader('Ganancia diaria promedio')
            c2.plotly_chart(fig,use_container_width=True)
        with t_bon:
            _now_=S.titpub.copy()
            _now_.set_index('simbolo',inplace=True)
            prof_bonos=calcular_proffit_bonos(S.operaciones,_now_)
            c1,c2=st.columns(2)
            fig=go.Figure()
            fig.add_trace(go.Bar(x=prof_bonos['Ganancia%'],y=prof_bonos.index,orientation='h',marker_color='#683CFC'))
            fig.update_layout(margin=dict(l=1, r=1, t=1, b=1))
            with c1.container(border=True):
                c11,c12=st.columns(2)
                val=0
                proff_av=0
                tot_ced=sum(prof_bonos['Cantidad'])
                for i in range(len(prof_bonos)):
                    val+=(prof_bonos.iloc[i]['Cantidad']*_now_.loc[prof_bonos.index[i],'ultimoPrecio'])
                    proff_av+=(prof_bonos.iloc[i]['Ganancia%']*prof_bonos.iloc[i]['Cantidad']/tot_ced)
                c11.metric('Total valuado',val)
                c12.metric('Ganancia Diaria Promedio',f'{round(proff_av,2)}%')
            c1.dataframe(prof_bonos.drop(columns=['Ganancia%']),use_container_width=True)
            c2.subheader('Ganancia diaria promedio')
            c2.plotly_chart(fig,use_container_width=True)

else:st.warning('No se ha podido iniciar sesion. Compruebe sus credenciales')