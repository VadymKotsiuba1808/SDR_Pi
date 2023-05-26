from __main__ import flask_app, get_app
from flask import request
from dateset import dataset_match



@flask_app.route('/api/2_4_ghz', methods=['POST'])
def receive_list():
    data_list = request.get_json()
    #print('Received list: ', data_list)

    res_cmp = dataset_match(data_list)
    get_app().flush_radar()
    if(len(res_cmp)>0):
        if '0' in res_cmp:
            print("Video")
            get_app().create_dot(180, 350)
        if  '1' in res_cmp:
            print("Microwave")
            get_app().create_dot(240, 150)

    return 'List received successfully'
