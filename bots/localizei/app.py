from flask import Flask, jsonify
from bot import Bot

APP = Flask(__name__)
APP.json.sort_keys = False

bot = Bot()

@APP.route('/consulta', methods=["POST"])
def consulta():
    try:
        result = bot.run()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'msg': str(e)}), 500



if __name__ == "__main__":
    APP.run(port=80, host='0.0.0.0')
