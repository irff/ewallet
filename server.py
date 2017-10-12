from flask import Flask
from flask import request, jsonify

from tinydb import TinyDB, Query

import requests
import json

app = Flask(__name__)
db = TinyDB('db.json')
DB = Query()

LIST_URL = 'http://152.118.31.2/list.php'
HALF_QUORUM = 4

@app.route('/ewallet/ping', methods=['GET', 'POST'])
def ping():
    response = {
        "pong" : 1
    }
    return jsonify(response)

@app.route('/ewallet/register', methods=['POST'])
def register():
    if request.method == 'POST':
        if quorum_check() > HALF_QUORUM:
            req = request.get_json()

            user_id = req.get('user_id', None)
            nama = req.get('nama', None)

            if user_id and nama:

                result = db.search(DB.user_id == user_id)
                if len(result) == 0:
                    db.insert({
                        'user_id' : user_id,
                        'nama' : nama,
                        'nilai_saldo' : 0
                    })
                    status = 1
                else:
                    status = -4
            else:
                status = -99
        else:
            status = -2

    else:
        status = -99

    response = {
        'status' : status
    }

    return jsonify(response)

@app.route('/ewallet/getSaldo', methods=['POST'])
def get_saldo():
    if request.method == 'POST':
        quorum_result = quorum_check()
        print quorum_result
        if quorum_result > HALF_QUORUM:
            req = request.get_json()
            print req

            user_id = req.get('user_id', None)

            if user_id:
                result = db.search(DB.user_id == user_id)
                if len(result) == 0:
                    nilai_saldo = -1
                else:
                    nilai_saldo = result[0]['nilai_saldo']
            else:
                nilai_saldo = -99
        else:
            nilai_saldo = -2
    else:
        nilai_saldo = -99

    response = {
        'status' : nilai_saldo
    }

    return jsonify(response)


def quorum_check():
    neighbors = [
        '1406543574',
        '1406579100',
        '1306398983',
        '1406543725',
        '1406527620',
        '1406527513',
        '1406527532',
        '1406543624'
    ]

    neighbor_ips = []

    # with open('list.json', "r") as listfile:
    #     ips = json.load(listfile)

    ips = requests.get(LIST_URL).json()

    for ip in ips:
        for neighbor in neighbors:
            if ip['npm'] == neighbor:
                neighbor_ips.append(ip['ip'])


    available = 0
    for neighbor_ip in neighbor_ips:
        url = 'http://' + neighbor_ip + '/ewallet/ping'
        try:
            status = requests.post(url, json={}, timeout=0.5)
            status = status.json()
            if status['pong'] == 1:
                available += 1
                print("url {} available".format(url))
            else:
                print("url {} not available".format(url))
        except:
            print("Can't connect to: {}", format(url))

    return available

def get_count(name):
    with open('data.json', "r+") as dbfile:
        content = json.load(dbfile)
        name_count = int(content.get(name, '0')) + 1

        content[name] = name_count

        dbfile.seek(0)
        dbfile.truncate()
        json.dump(content, dbfile)
        return name_count