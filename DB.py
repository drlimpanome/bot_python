from flask import Flask, request, jsonify
from sqlalchemy import create_engine
from sqlalchemy import text
import requests
import functools
from lxml import etree

from urllib.parse import quote

db_user = "manychat"
db_password = quote("1Nh4vez@5bH42mmk7)_H<dm@mA")
db_host = "ec2-23-23-53-208.compute-1.amazonaws.com"
db_name = "drlimpanome"  # Presumindo que o nome do banco de dados permanece o mesmo

DATABASE_URL = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:3306/{db_name}"

# DATABASE_URL = 'mysql+pymysql://manychat:1Nh4vez@5bH42mmk7)_H<dm@mA@localhost:3306/drlimpanome'
engine = create_engine(DATABASE_URL)

APP = Flask(__name__)
APP.json.sort_keys = False

def db_conn(func):
    @functools.wraps(func)
    def wrapper():
        try:
            conn = engine.connect()
            resultado = func(conn)
            conn.close()
            return jsonify(resultado), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return wrapper

@db_conn
def get_all_cpfs(conn) -> list[str]:
    sql = 'SELECT documento, max(id_ticket) as id_ticket FROM tbconsultas WHERE status_id = 1 group by documento'
    result = conn.execute(text(sql))
    if result.rowcount > 0:
        return [{'documento': row[0], 'id_ticket': row[1]} for row in result.fetchall() if row[0] is not None]
    return []

@db_conn
def get_all_cpfs_for_retry(conn) -> list[str]:
    sql = 'SELECT documento, max(id_ticket) as id_ticket FROM tbconsultas WHERE status_id = 4 group by documento'
    result = conn.execute(text(sql))
    if result.rowcount > 0:
        return [{'documento': row[0], 'id_ticket': row[1]} for row in result.fetchall() if row[0] is not None]
    return []

@db_conn
def update_status_consult(conn):
    payload = request.get_json()
    id = payload.get('id')
    status = payload.get('status')
    bot = payload.get('bot')
    if not id or not status or not bot:
        raise Exception('Erro ao enviar id ou status')
    
    sql = (
        'UPDATE tbconsultas SET status_id = :status, updated_at = current_timestamp(), updated_by = :bot WHERE id_ticket = :id'
    )
    result = conn.execute(text(sql), {'status': status, 'id': id, 'bot': bot})
    conn.commit()
    return result.rowcount > 0

@db_conn
def update_debt_value(conn):
    payload = request.get_json()
    id = payload.get('id')
    value = payload.get('value')
    if not id or not value:
        raise Exception('Erro ao enviar id ou value')
    
    sql = 'UPDATE tbconsultas SET divida = :value WHERE id_ticket = :id'
    result = conn.execute(text(sql), {'value': value, 'id': id})
    conn.commit()
    return result.rowcount > 0

@db_conn
def set_file_url(conn):
    payload = request.get_json()
    id = payload.get('id')
    url = payload.get('url')
    if not id or not url:
        raise Exception('Erro ao enviar id ou url')
    
    sql = 'UPDATE tbconsultas SET url = :url WHERE id_ticket = :id'
    result = conn.execute(text(sql), {'url': url, 'id': id})
    conn.commit()
    return result.rowcount > 0

def get_token_confere():
    try:
        url_home = 'https://confere.link/'
        login = 'new_n/logar.asp'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        payload = {
            'login': 'claudio.tomich.drlimpanome@gmail.com',
            'senha': 'YX6387YV'
        }

        session = requests.Session()
        session.headers.update(headers)

        response = session.post(url_home + login, data=payload)

        dict_cookies = response.cookies.get_dict()
        value_cookies = dict_cookies.get('ASPSESSIONIDCCTBBBDA')
        cookies = {
            'Cookie': value_cookies
        }
        response2 = session.get(url_home, cookies=cookies)

        page_xml = etree.HTML(response2.text)
        elem_tk = page_xml.xpath('//input[@name="token"]')
        if len(elem_tk) == 0:
            raise Exception('Erro ao obter token')
        return jsonify({'token': elem_tk[0].get('value')}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

APP.add_url_rule('/get_cpfs', methods=['GET'], view_func=get_all_cpfs)
APP.add_url_rule('/get_cpfs_for_retry', methods=['GET'], view_func=get_all_cpfs_for_retry)
APP.add_url_rule('/update_status', methods=['PUT'], view_func=update_status_consult)
APP.add_url_rule('/update_divida', methods=['PUT'], view_func=update_debt_value)
APP.add_url_rule('/update_url', methods=['PUT'], view_func=set_file_url)
APP.add_url_rule('/get_token_confere', methods=['GET'], view_func=get_token_confere)

if __name__ == "__main__":
    APP.run(host='0.0.0.0', port=81)
