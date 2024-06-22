import requests
from datetime import datetime, timedelta
import pandas as pd

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
        port_df['tipo']=tipos.replace('TitulosPublicos', 'Bonos').replace('FondoComundeInversion','FCI')
        port_df['valorizado%']=round(100*port_df['valorizado']/sum(port_df['valorizado']),2)
        port_df['gananciaDiariaPonderada'] = port_df['variacionDiaria'] * port_df['valorizado%']
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
        #df.set_index('simbolo',inplace=True)
        return df