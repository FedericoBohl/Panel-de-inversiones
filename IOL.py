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
        self.his_url = f'{self.base_url}/bCBA/Titulos/{{ticker}}/Cotizacion/seriehistorica/2023-01-01/{{date}}/sinAjustar'
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
        url = self.quotes_url.format(instrument=instrument, country=('argentina' if instrument!='aDRs' else "estados_Unidos"))
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
    def get_his(self,ticker):
        self.ensure_token()
        url = self.his_url.format(ticker=ticker,date='2024-08-30')#datetime.today().strftime('%Y-%m-%d'))
        headers = {'Authorization': f"Bearer {self.token_info['access_token']}"}
        response = requests.get(url=url,headers=headers)
        if response.status_code != 200:
            try:
                self.refresh_token()
                response = requests.get(url=url,headers=headers)
                if response.status_code != 200:
                    raise Exception(f"Error fetching {ticker} quotes: {response.text}")
            except: raise Exception(f"Error fetching {ticker} quotes: {response.text}")
        df=pd.DataFrame(response.json())
        df=df[['ultimoPrecio','fechaHora']]
        return df  
    
    def get_operaciones_hist(self):
        self.ensure_token()
        operaciones_url = f"{self.base_url}/operaciones?filtro.estado=todas&filtro.fechaDesde=2020-01-01&filtro.fechaHasta={datetime.today().strftime('%Y-%m-%d')}&filtro.pais=argentina"
        headers = {'Authorization': f"Bearer {self.token_info['access_token']}"}
        response = requests.get(operaciones_url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Error fetching portfolio: {response.text}")
        df=pd.DataFrame(response.json())
        df['fechaOperada'] = pd.to_datetime(df['fechaOperada'].str.split('T').str[0], format='%Y-%m-%d', errors='coerce')
        df['fechaOrden'] = pd.to_datetime(df['fechaOrden'].str.split('T').str[0], format='%Y-%m-%d', errors='coerce')
        #df['fechaOperada']=df['fechaOperada'].dt.strftime('%Y-%m-%d')
        #df = df[df['fechaOperada'].notna()]
        #Ajuste por los BOPREALES
        filtro = (df['tipo'] == 'Pago de Amortización')
        cantidad_vendida=0
        filtered_df = df[(df['simbolo'] == 'BPO27') & (df['fechaOperada'] < pd.Timestamp('2024-03-01'))]
        for index, row in filtered_df.iterrows():
            if row['tipo'] == 'Compra':
                cantidad_vendida += row['cantidadOperada']
            elif row['tipo'] == 'Venta':
                cantidad_vendida -= row['cantidadOperada']
        df.loc[(filtro & (df['simbolo']=='BPO27')), 'cantidadOperada'] = cantidad_vendida
        df.loc[(filtro & (df['simbolo']=='BPO27')), 'precioOperado'] = 7100
        df.loc[(filtro & (df['simbolo']=='BPO27')), 'montoOperado'] = 7100*cantidad_vendida
        df.loc[(filtro & (df['simbolo']=='BPO27')), 'fechaOperada'] = pd.Timestamp('2024-03-01')
        df.loc[(filtro & (df['simbolo']=='BPO27')), 'tipo'] = 'Venta'
        precios = {
            'BPOA7': 8500,
            'BPOB7': 7500,
            'BPOC7': 6500,
            'BPOD7': 5800
        }
        # Actualizar las filas de los nuevos bonos a "Compra" con sus precios y montos
        for simbolo, precio in precios.items():
            filtro_bono = filtro & (df['simbolo'] == simbolo)
            df.loc[filtro_bono, 'precioOperado'] = precio
            df.loc[filtro_bono, 'montoOperado'] = precio * df.loc[filtro_bono, 'cantidadOperada']
            df.loc[filtro_bono, 'fechaOperada'] = pd.Timestamp('2024-03-01')
            df.loc[filtro_bono, 'tipo'] = 'Compra'

        df=df[df['tipo'].isin(['Compra', 'Venta'])]
        df=df[df['estado']=='terminada']
        df=df[['tipo','fechaOperada','simbolo','cantidadOperada','montoOperado','precioOperado']]
        df=df.sort_values(by='fechaOperada', ascending=True)
        return df
    
    def get_operaciones(self,acciones_now,cedears_now,titpub,letras):
        self.ensure_token()
        operaciones_url = f"{self.base_url}/operaciones?filtro.estado=todas&filtro.fechaDesde=2020-01-01&filtro.fechaHasta={datetime.today().strftime('%Y-%m-%d')}&filtro.pais=argentina"
        headers = {'Authorization': f"Bearer {self.token_info['access_token']}"}
        response = requests.get(operaciones_url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Error fetching portfolio: {response.text}")
        df=pd.DataFrame(response.json())
        df['fechaOperada'] = pd.to_datetime(df['fechaOperada'].str.split('T').str[0], format='%Y-%m-%d', errors='coerce')
        df['fechaOrden'] = pd.to_datetime(df['fechaOrden'].str.split('T').str[0], format='%Y-%m-%d', errors='coerce')
        #df['fechaOperada']=df['fechaOperada'].dt.strftime('%Y-%m-%d')
        #df = df[df['fechaOperada'].notna()]
        #Ajuste por los BOPREALES
        filtro = (df['tipo'] == 'Pago de Amortización')
        cantidad_vendida=0
        filtered_df = df[(df['simbolo'] == 'BPO27') & (df['fechaOperada'] < pd.Timestamp('2024-03-01'))]
        for index, row in filtered_df.iterrows():
            if row['tipo'] == 'Compra':
                cantidad_vendida += row['cantidadOperada']
            elif row['tipo'] == 'Venta':
                cantidad_vendida -= row['cantidadOperada']
        df.loc[(filtro & (df['simbolo']=='BPO27')), 'cantidadOperada'] = cantidad_vendida
        df.loc[(filtro & (df['simbolo']=='BPO27')), 'precioOperado'] = 7100
        df.loc[(filtro & (df['simbolo']=='BPO27')), 'montoOperado'] = 7100*cantidad_vendida
        df.loc[(filtro & (df['simbolo']=='BPO27')), 'fechaOperada'] = pd.Timestamp('2024-03-01')
        df.loc[(filtro & (df['simbolo']=='BPO27')), 'tipo'] = 'Venta'
        precios = {
            'BPOA7': 8500,
            'BPOB7': 7500,
            'BPOC7': 6500,
            'BPOD7': 5800
        }
        # Actualizar las filas de los nuevos bonos a "Compra" con sus precios y montos
        for simbolo, precio in precios.items():
            filtro_bono = filtro & (df['simbolo'] == simbolo)
            df.loc[filtro_bono, 'precioOperado'] = precio
            df.loc[filtro_bono, 'montoOperado'] = precio * df.loc[filtro_bono, 'cantidadOperada']
            df.loc[filtro_bono, 'fechaOperada'] = pd.Timestamp('2024-03-01')
            df.loc[filtro_bono, 'tipo'] = 'Compra'

        df=df[df['tipo'].isin(['Compra', 'Venta'])]
        df=df[df['estado']=='terminada']
        df=df[['tipo','fechaOperada','simbolo','cantidadOperada','montoOperado','precioOperado']]
        df=df.sort_values(by='fechaOperada', ascending=True)
        kind=[]
        for i in df.values.tolist():
            _='Accion' if i[2] in acciones_now['simbolo'].to_list() else ('Cedear' if i[2] in cedears_now['simbolo'].to_list() else ('Bono' if i[2] in titpub['simbolo'].to_list() else ('Letra' if i[2] in letras['simbolo'].to_list() else None)))
            kind.append(_)
        df['Tipo de Acción']=kind
        df.columns=['Tipo Transacción','Fecha Liquidación','Simbolo','Cantidad','Monto','Precio Ponderado','Tipo de Acción']
        return df 