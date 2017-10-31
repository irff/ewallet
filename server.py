from flask import Flask
from flask import request, jsonify
from tinydb import TinyDB, Query
import requests

app = Flask(__name__)

# Use TinyDB
db = TinyDB('db.json')
DB = Query()

# Initialize important constants
LIST_URL = 'http://152.118.31.2/list.php'
MAX_TRANSFER_AMOUNT = 1000000000
ZERO_QUORUM = 0
HALF_QUORUM = 5
FULL_QUORUM = 8

# ======== HELPER METHODS ========

# return IPs of neighbors corresponding to a list of IDs
def get_neighbor_ips():
    neighbors = [
        '1406543763',
        '1406543574',
        '1406579100',
        '1306398983',
        '1406543725',
        '1406527620',
        '1406527513',
        '1406572025',
    ]

    neighbor_ips = []

    ips = requests.get(LIST_URL).json()

    for ip in ips:
        for neighbor in neighbors:
            if ip['npm'] == neighbor:
                neighbor_ips.append(ip['ip'])

    return neighbor_ips


# return IP address of first IP that has user_id as member
# return -1 if can't get user_id on all nodes
def pass_get_total_saldo(user_id):
    neighbor_ips = get_neighbor_ips()
    for neighbor_ip in neighbor_ips:
        url = 'http://' + neighbor_ip + '/ewallet/getSaldo'
        try:
            response = requests.post(url, json={
                'user_id': user_id
            }, timeout=1)
            response = response.json()
            if response['nilai_saldo'] >= 0:
                # call getTotalSaldo
                next_url = 'http://' + neighbor_ip + '/ewallet/getTotalSaldo'
                try:
                    response = requests.post(next_url, json={
                        'user_id': user_id
                    }, timeout=2)
                    response = response.json()
                    print("[passGetTotalSaldo] Sucessfully getting saldo of: {}, from {}".format(response['nilai_saldo'], neighbor_ip))
                    return response['nilai_saldo']
                except Exception as e:
                    print(e)
                    print("[passGetTotalSaldo] Error getTotalSaldo from {}".format(neighbor_ip))
        except Exception as e:
            print(e)
            print("[passGetTotalSaldo] Can't connect to: {}".format(url))

    return -1


# return -3 if can't connect to one of the host
# return >=0 as the total saldo if successful
def get_neighbors_total_saldo(user_id):
    total_saldo = 0
    neighbor_ips = get_neighbor_ips()
    for neighbor_ip in neighbor_ips:
        url = 'http://' + neighbor_ip + '/ewallet/getSaldo'
        try:
            print("[getNeighborsSaldo] Trying to connect to: {}".format(neighbor_ip))
            response = requests.post(url, json={
                'user_id': user_id
            }, timeout=1)
            response = response.json()
            print("[getNeighborsSaldo] Finished connecting to: {}".format(neighbor_ip))

            if response['nilai_saldo'] >= 0:
                print("[getNeighborsSaldo] Succesfully adding: {}, from {}".format(response['nilai_saldo'], neighbor_ip), )
                nilai_saldo = response['nilai_saldo']
                total_saldo += nilai_saldo
            else:
                print("[getNeighborsSaldo] Failed getting saldo from {}".format(neighbor_ip))
        except Exception as e:
            print(e)
            print("[getNeighborsSaldo] Can't connect to: {}".format(url))
            return -3

    return total_saldo

# return the number of available neighbors
def quorum_check():
    neighbor_ips = get_neighbor_ips()

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
            print("Can't connect to: {}".format(url))

    return available


# ======== ROUTING ========
@app.route('/ewallet/ping', methods=['GET', 'POST'])
def ping():
    if request.method == 'POST':
        pong = 1
    else:
        pong = -99

    response = {
        "pong" : pong
    }   
    return jsonify(response)

@app.route('/ewallet/register', methods=['POST'])
def register():
    if request.method == 'POST':
        if quorum_check() >= HALF_QUORUM:
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
                    status_register = 1
                else:
                    status_register = -4
            else:
                status_register = -99
        else:
            status_register = -2

    else:
        status_register = -99

    response = {
        'status_register' : status_register
    }

    return jsonify(response)

@app.route('/ewallet/getSaldo', methods=['POST'])
def get_saldo():
    if request.method == 'POST':
        quorum_result = quorum_check()
        if quorum_result >= HALF_QUORUM:
            req = request.get_json()

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
        'nilai_saldo' : nilai_saldo
    }

    return jsonify(response)

@app.route('/ewallet/transfer', methods=['POST'])
def trasfer():
    if request.method == 'POST':
        quorum_result = quorum_check()
        if quorum_result >= HALF_QUORUM:
            req = request.get_json()
            user_id = req.get('user_id', None)
            nilai = req.get('nilai', None)

            if user_id and nilai:
                result = db.search(DB.user_id == user_id)
                if len(result) > 0:
                    nilai = int(nilai)
                    if(nilai >= 0 and nilai <= MAX_TRANSFER_AMOUNT):
                        saldo_awal = result[0]['nilai_saldo']
                        db.update({
                            'nilai_saldo' : saldo_awal + nilai
                        }, DB.user_id == user_id)
                        status_transfer = 1
                    else:
                        status_transfer = -5
                else:
                    status_transfer = -4
            else:
                status_transfer = -99
        else:
            status_transfer = -2
    else:
        status_transfer = -99

    response = {
        'status_transfer': status_transfer
    }

    return jsonify(response)

@app.route('/ewallet/getTotalSaldo', methods=['POST'])
def get_total_saldo():
    if request.method == 'POST':
        quorum_result = quorum_check()
        if quorum_result >= FULL_QUORUM:
            req = request.get_json()

            user_id = req.get('user_id', None)
            if user_id:
                result = db.search(DB.user_id == user_id)
                if len(result) == 0:
                    print("[getTotalSaldo] Passing getTotalSaldo command to neighbor")
                    nilai_saldo = pass_get_total_saldo(user_id)
                else:
                    print("[getTotalSaldo] Getting saldo of all neighbors")
                    total_saldo = get_neighbors_total_saldo(user_id)
                    if total_saldo >= 0:
                        nilai_saldo = total_saldo
                    else:
                        nilai_saldo = -3

            else:
                nilai_saldo = -99
        else:
            nilai_saldo = -2
    else:
        nilai_saldo = -99

    response = {
        'nilai_saldo' : nilai_saldo
    }

    return jsonify(response)

# Run on localhost port 80, allow all connection, allow multi-threading
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80, threaded=True)
