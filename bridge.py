from flask import Flask, request

app = Flask(__name__)


@app.route('/api/2_4_ghz', methods=['POST'])
def receive_list():
    data_list = request.get_json()
    print('Received list: ', data_list)

    return 'List received successfully'

app.run(host='0.0.0.0')