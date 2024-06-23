import requests
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st


class TokenManager:
    def __init__(self, username,password):
        self.token_info = None
        self.user_data={
                        'username':username,
                        'password':password
                        }
        self.load_user_data()
        self.token_url = 'https://api.invertironline.com/token'
        self.base_url = 'https://api.invertironline.com/api/v2'
        self.portfolio_url = f'{self.base_url}/portafolio'
        self.quotes_url = f'{self.base_url}/Cotizaciones/{{instrument}}/{{country}}/Todos'
        self.get_new_token()

    def load_user_data(self):
        self.username = self.user_data['username']
        self.password = self.user_data['password']

    def get_new_token(self):
        data = {
            'grant_type': 'password',
            'username': self.username,
            'password': self.password
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post(self.token_url, data=data, headers=headers)
        self.token_info = response.json()
        if 'error' in self.token_info:
            raise Exception(f"Error obtaining token: {self.token_info['error']}")
        self.token_info['expires_at'] = datetime.now() + timedelta(seconds=self.token_info['expires_in'])
    
    def refresh_token(self):
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.token_info['refresh_token']
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post(self.token_url, data=data, headers=headers)
        new_token_info = response.json()
        if 'error' in new_token_info:
            raise Exception(f"Error refreshing token: {new_token_info['error']}")
        self.token_info.update(new_token_info)
        self.token_info['expires_at'] = datetime.now() + timedelta(seconds=self.token_info['expires_in'])

    def ensure_token(self):
        if (not self.token_info) or (datetime.now() >= self.token_info['expires_at']):
            self.refresh_token() if self.token_info else self.get_new_token()

    def get_portfolio(self):
        self.ensure_token()
        headers = {'Authorization': f"Bearer {self.token_info['access_token']}"}
        response = requests.get(self.portfolio_url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Error fetching portfolio: {response.text}")
        port_df=pd.DataFrame(response.json()['activos'])
        tickers=[equity['simbolo'] for equity in port_df['titulo'].to_list()]
        tipos=[equity['tipo'] for equity in port_df['titulo'].to_list()]
        port_df=port_df.drop(columns=['cantidad','comprometido','puntosVariacion','ultimoPrecio','ppc','gananciaPorcentaje','gananciaDinero','parking','titulo'])
        port_df['simbolo']=tickers
        port_df['tipo']=tipos
        port_df['tipo']=port_df['tipo'].replace('TitulosPublicos', 'Bonos')
        port_df['tipo']=port_df['tipo'].replace('FondoComundeInversion','FCI')
        port_df['valorizado%']=round(100*port_df['valorizado']/sum(port_df['valorizado']),2)
        port_df['gananciaDiariaPonderada'] = port_df['variacionDiaria'] * port_df['valorizado%']/100
        return port_df

    def get_quotes(self, instrument):
        self.ensure_token()
        url = self.quotes_url.format(instrument=instrument, country='argentina')
        headers = {'Authorization': f"Bearer {self.token_info['access_token']}"}
        response = requests.get(url=url,headers=headers)
        if response.status_code != 200:
            try:
                self.refresh_token()
                response = requests.get(url=url,headers=headers)
                if response.status_code != 200:
                    raise Exception(f"Error fetching {instrument} quotes: {response.text}")
            except: raise Exception(f"Error fetching {instrument} quotes: {response.text}")
        df=pd.DataFrame(response.json()['titulos'])
        df=df[['simbolo','ultimoPrecio','variacionPorcentual']]
        df=df.rename(columns={'variacionPorcentual':'Var%'})
        return df
    
    def get_operaciones(self,acciones_now,cedears_now,titpub):
        self.ensure_token()
        operaciones_url = f"{self.base_url}/operaciones?filtro.estado=todas&filtro.fechaDesde=2020-01-01&filtro.fechaHasta={datetime.today().strftime('%Y-%m-%d')}&filtro.pais=argentina"
        headers = {'Authorization': f"Bearer {self.token_info['access_token']}"}
        response = requests.get(operaciones_url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Error fetching portfolio: {response.text}")
        df=pd.DataFrame(response.json())
        #df=df.set_index('numero',inplace=True)
        st.dataframe(df)
        df['fechaOperada']=pd.to_datetime(df['fechaOperada'])

        #Ajuste por los BOPREALES
        filtro = (df['tipo'] == 'Pago de Amortización')
        cantidad_vendida=0
        for i in df[df['simbolo']=='BPO27' & df['fechaOperada']<pd.Timestamp('2024-03-01')].values.tolist():
            if i[2]=='Compra':cantidad_vendida+=i[6]
            elif i[2]=='Venta':cantidad_vendida-=i[6]
            else:continue
        df.loc[(filtro & df['simbolo']=='BPO27'), 'cantidadOperada'] = cantidad_vendida
        df.loc[(filtro & df['simbolo']=='BPO27'), 'precioOperado'] = 71000
        df.loc[(filtro & df['simbolo']=='BPO27'), 'montoOperado'] = 71000*cantidad_vendida
        df.loc[(filtro & df['simbolo']=='BPO27'), 'tipo'] = 'Venta'

        df.loc[(filtro & df['simbolo']=='BPOA7'), 'precioOperado'] = 85000
        df.loc[(filtro & df['simbolo']=='BPOA7'), 'montoOperado'] = 85000*df.loc[(filtro & df['simbolo']=='BPOA7'), 'cantidadOperada']
        df.loc[(filtro & df['simbolo']=='BPOA7'), 'tipo'] = 'Compra'
        df.loc[(filtro & df['simbolo']=='BPOB7'), 'precioOperado'] = 75000
        df.loc[(filtro & df['simbolo']=='BPOB7'), 'montoOperado'] = 85000*df.loc[(filtro & df['simbolo']=='BPOB7'), 'cantidadOperada']
        df.loc[(filtro & df['simbolo']=='BPOB7'), 'tipo'] = 'Compra'
        df.loc[(filtro & df['simbolo']=='BPOC7'), 'precioOperado'] = 65000
        df.loc[(filtro & df['simbolo']=='BPOC7'), 'montoOperado'] = 85000*df.loc[(filtro & df['simbolo']=='BPOC7'), 'cantidadOperada']
        df.loc[(filtro & df['simbolo']=='BPOC7'), 'tipo'] = 'Compra'
        df.loc[(filtro & df['simbolo']=='BPOD7'), 'precioOperado'] = 58000
        df.loc[(filtro & df['simbolo']=='BPOD7'), 'montoOperado'] = 85000*df.loc[(filtro & df['simbolo']=='BPOD7'), 'cantidadOperada']
        df.loc[(filtro & df['simbolo']=='BPOD7'), 'tipo'] = 'Compra'

        #BPOA7: 85.000
        #BPOB7: 75.000
        #BPOC7: 65.000
        #BPOD7: 58.000
        #BPO27: 71.000
        #Buscar en donde tipo es Pago de Amortización
        #Filtrar por que arranque en BOP y buscar donde cantidadOperada!=None
        df=df[df['tipo'].isin(['Compra', 'Venta'])]
        df=df[df['estado']=='terminada']
        df=df[['tipo','fechaOperada','simbolo','cantidadOperada','montoOperado','precioOperado']]
        df=df.sort_values(by='fechaOperada', ascending=True)
        kind=[]
        for i in df.values.tolist():
            _='Accion' if i[2] in acciones_now['simbolo'].to_list() else ('Cedear' if i[2] in cedears_now['simbolo'].to_list() else ('Bono' if i[2] in titpub['simbolo'].to_list() else None))
            kind.append(_)
        df['Tipo de Acción']=kind
        df.columns=['Tipo Transacción','Fecha Liquidación','Simbolo','Cantidad','Monto','Precio Ponderado','Tipo de Acción']
        return df