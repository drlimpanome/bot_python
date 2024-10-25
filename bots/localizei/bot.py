from flask import request
import requests
from lxml import etree
from twocaptcha import TwoCaptcha
import json
import urllib.parse
import os
import re
from dotenv import load_dotenv


load_dotenv()

URL_CONFERE = 'https://app.localizei.app/'
HEADERS = {
  'accept': '*/*',
  'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
  'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
  'origin': 'https://app.localizei.app',
  'priority': 'u=1, i',
  'referer': 'https://app.localizei.app/',
  'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': "Windows",
  'sec-fetch-dest': 'empty',
  'sec-fetch-mode': 'cors',
  'sec-fetch-site': 'same-origin',
  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
  'x-requested-with': 'XMLHttpRequest'
}

MODAL_XPATH = '//div[@role="dialog"][@aria-hidden="true"]'

PROXY_USER = 'robotcaixa2022'
PROXY_PASSWORD = 'direto2022'
http = "23.129.255.11:5419"

proxy = {'http': f"http://{PROXY_USER}:{PROXY_PASSWORD}@{http}",
                     'https': f"http://{PROXY_USER}:{PROXY_PASSWORD}@{http}"}

class Bot():
    
    def __init__(self):
        self.session = None


    @staticmethod
    def redundancia(data):
        temp_dict = {}
        for key in data.keys():
            temp_dict[key] = []
            for item in data[key]:
                for i in temp_dict[key]:
                    if item.get('data') == i.get('data') and item.get('valor') == i.get('valor'):
                        if not item.get('contrato'):
                            continue
                        else:
                            if item.get('contrato') == i.get('contrato'):
                                continue

                temp_dict[key].append(item)
        return temp_dict

    @staticmethod
    def get_total(data):
        all_debts = [j for i in data.keys() for j in data[i]]
        return round(sum(list(map(lambda x: float(x.get('valor')), all_debts))), 2)

    def run(self):
        payload = request.get_json()
        doc = payload.get('doc')
        if not doc:
            raise DocumentNotFound()
        
        doc_clean = self.clean_doc(doc)
        valid_doc = self.doc_validate(doc_clean)
        if not valid_doc:
            raise InvalidDocument()
        
        if not self.session:
            self.login()

        text_data = self.consulta(doc_clean)
        if not text_data:
            raise UncatalogedError()
        
        xml = etree.HTML(text_data)
        customer_xpath = '/div/div/div[2]/div[1]/div[2]/h3/strong/text()'
        customer_name = xml.xpath(MODAL_XPATH + customer_xpath)
        if not customer_name:
            print("customer_name: ", customer_name)
        else:
            customer_name = customer_name[0].strip()

        data = self.recuperar_dados(xml)
        final_data = self.redundancia(data)
        total = self.get_total(final_data)

        # xml_pdf = xml.xpath(MODAL_XPATH + '/div')
        # if not xml_pdf:
        #     return 'sem modal pdf'
        # xml_pdf = xml_pdf[0]
        # pdf_base64 = get_pdf(xml_pdf, doc)

        return {
            "nome": customer_name,
            "documento": doc_clean,
            "total": total,
            "dividas": final_data
        }

    @staticmethod
    def resolve_captcha(site_key):
        key_TC = os.getenv("KEY_TC")
        solver = TwoCaptcha(key_TC)
        try:
            return solver.recaptcha(
                sitekey=site_key,
                url=URL_CONFERE)

        except Exception as e:
            print(e)

    def get_site_key(self):
        self.session = requests.Session()
        response = self.session.get(URL_CONFERE, proxies=proxy)
        xml = etree.HTML(response.text)
        print(response.text)
        site_key = xml.xpath('//div[@class="g-recaptcha"][@data-sitekey]')
        print(site_key)
        if site_key:
            return site_key[0].get('data-sitekey')


    def login(self):
        login = os.getenv("LOGIN")
        password = os.getenv("PASSWORD")
        try:
            site_key = self.get_site_key()
            recaptcha_response = self.resolve_captcha(site_key)
            payload = f'login={login}&senha={password}&grecaptcharesponse={recaptcha_response.get("code")}&olhaoespertinhoai=malandrinho&acao=0'
            response = self.session.post(URL_CONFERE, headers=HEADERS, data=payload, allow_redirects=False, proxies=proxy)
            return response.status_code == 200
        except Exception as e:
            print('erro login: ', str(e))
            return None
        
    @staticmethod
    def clean_doc(doc):
        return ''.join(filter(str.isdigit, doc))

    
    def doc_validate(self, doc):
        if len(doc) == 11:
            if doc == doc[0] * 11:
                return False
            return self.validar_cpf(doc)
        
        elif len(doc) == 14:
            if doc == doc[0] * 14:
                return False
            return self.validar_cnpj(doc)


    def consulta(self, doc):
        key_doc = f"cpf={doc}" if len(doc) == 11 else f"cnpj={doc}" 
        payload = f"{key_doc}&oi=tepeguei&registro=1"
        response = self.session.post(URL_CONFERE + 'dividas2/', headers=HEADERS, data=payload, allow_redirects=False, proxies=proxy)
        if 'seu usuário foi deslogado' in response.text:
            self.login()
            return self.consulta(doc)
        return response.text
    

    def get_pdf(self, data, doc):
        txt_xml = etree.tostring(data, encoding='unicode')
        txt_encoded = urllib.parse.quote(txt_xml)
        final_txt = txt_encoded.replace('%20', '+')
        payload = f"conteudo={final_txt}&titulo=Localizei-D%C3%ADvidas+-+2.0-{doc}&gerarpdf=1"
        response = self.session.post(URL_CONFERE + "dividas2/externo/", headers=HEADERS, data=json.dumps(payload), allow_redirects=False, proxies=proxy)
        if response.status_code == 200:
            return response.text

    @staticmethod
    def get_data(row):
        text =  row.xpath('.//td')[0].text
        if not text:
            return None
        
        regex = r"\s*:\s*(\d{2}/\d{2}/\d{4})[\s\S]*?\s*:\s*R\$\s*([\d,.]+)[\s\S]"
        match = re.search(regex, text)
        if not match:
            return None
        
        temp = {
            "data": match.group(1),
            "valor": float(re.sub(r'\.', '', match.group(2)).replace(',', '.'))
        }
        
        regex_contrato = r"Contrato\s*:\s*(\d+)"
        contrato = re.search(regex_contrato, text)
        if contrato:
            temp['contrato'] = contrato.group(1)

        return temp


    def recuperar_dados(self, xml):
        response = {}
        table_xpath = '//div[5]/div[2]/table/tbody'
        relevant_tables = ['spc', 'scpc', 'serasa']

        table_xml = xml.xpath(MODAL_XPATH + table_xpath)
        if not table_xml:
            print('table_xml: ', table_xml)

        sistema = None
        list_rows = table_xml[0].xpath('tr')
        for row in list_rows:
            has_sistema = row.xpath('.//b')     
            if has_sistema and has_sistema[0].text.lower() in relevant_tables:
                sistema = has_sistema[0].text
            
            if has_sistema[0].text.lower() != 'ocorrência' and not has_sistema[0].text.lower() in relevant_tables:
                sistema = None

            if not sistema:
                continue

            if response.get(sistema) is None:
                response[sistema] = []
                continue

            data = self.get_data(row)
            if not data:
                continue

            response[sistema].append(data)
        return response

    @staticmethod
    def validar_cpf(cpf):
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        digito1 = (soma * 10 % 11) % 10
        if digito1 != int(cpf[9]):
            return False

        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        digito2 = (soma * 10 % 11) % 10
        if digito2 != int(cpf[10]):
            return False

        return True

    @staticmethod
    def validar_cnpj(cnpj: str) -> bool:
        peso1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(cnpj[i]) * peso1[i] for i in range(12))
        digito1 = (soma % 11)
        digito1 = 0 if digito1 < 2 else 11 - digito1
        if digito1 != int(cnpj[12]):
            return False

        peso2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(cnpj[i]) * peso2[i] for i in range(13))
        digito2 = (soma % 11)
        digito2 = 0 if digito2 < 2 else 11 - digito2
        if digito2 != int(cnpj[13]):
            return False

        return True


class InvalidDocument(Exception):
    def __init__(self, error=None) -> None:
        self.message = f'documento invalido'
        self.error = error

    def __str__(self):
        message = self.message
        if self.error:
            message += f': {self.error}'
        return message
    
class DocumentNotFound(Exception):
    def __init__(self, error=None) -> None:
        self.message = f'documento nao encontrado'
        self.error = error

    def __str__(self):
        message = self.message
        if self.error:
            message += f': {self.error}'
        return message

class UncatalogedError(Exception):
    def __init__(self, error=None) -> None:
        self.message = f'erro nao catalogado'
        self.error = error

    def __str__(self):
        message = self.message
        if self.error:
            message += f': {self.error}'
        return message
