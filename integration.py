import time
import schedule
import requests
from datetime import datetime as dt

URL_DB = 'http://localhost:81/'
URL_CONFERE = 'http://localhost:80/consultDocument/'


def get_all_docs():
    respose = requests.get(URL_DB + 'get_cpfs')
    print(respose.text)
    if respose.status_code != 200:
        raise Exception('Erro ao obter a lista de cpfs')
    return respose.json()

def get_all_docs_for_retry():
    respose = requests.get(URL_DB + 'get_cpfs_for_retry')
    if respose.status_code != 200:
        raise Exception('Erro ao obter a lista de cpfs de retentativa')
    return respose.json()

def update_status(payload_default, status):
    payload = payload_default
    payload['status'] = status
    payload['bot'] = 'bot_confere'
    response = requests.put(URL_DB + 'update_status', json=payload)
    if response.status_code != 200:
        raise Exception(str(response.content))
    
def update_divida(payload_default, divida):
    payload = payload_default
    payload['value'] = divida
    payload['bot'] = 'bot_confere'
    payload['status'] = '4'
    response = requests.put(URL_DB + 'update_divida', json=payload)
    if response.status_code != 200:
        raise Exception(str(response.content))
    
def update_url(payload_default, url):
    payload = payload_default
    payload['url'] = url
    response = requests.put(URL_DB + 'update_url', json=payload)
    if response.status_code != 200:
        raise Exception(str(response.content))
    
def run(retry=False):
    try:
        all_docs = get_all_docs() if not retry else get_all_docs_for_retry()
        if not all_docs:
            return
        
        for doc in all_docs:
            id_ticket = doc.get('id_ticket')
            documento = doc.get('documento')
            payload_default = {'id': id_ticket}
            
            try:
                update_status(payload_default, status='2')
                
                payload = {
                    "numeroDocumento": documento
                }
                response = requests.post(URL_CONFERE + id_ticket, json=payload)
                if response.status_code != 200:
                    raise Exception(f'status.code: {response.status_code} - msg: {response.content}')
                
                response_json = response.json()
                divida = response_json.get('totalDebt')
                update_divida(payload_default, divida)

                pdf_url = response_json.get('pdfUrl')
                update_url(payload_default, pdf_url)

                update_status(payload_default, status='3')

            except Exception as e:
                print(f"{dt.now().strftime('%d/%m/%Y %H:%M')} - error: {str(e)}")
                update_status(payload_default, status='4')
    except Exception as error:
        print('ERROR: ', str(error))


def retentativa():
    run(retry=True)


schedule.every(5).minutes.do(run)
schedule.every(3).minutes.do(retentativa)

if __name__=='__main__':
    run()
    while True:
        schedule.run_pending()
        time.sleep(1)
