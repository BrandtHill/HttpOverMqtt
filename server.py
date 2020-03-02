import requests
import paho.mqtt.client as mqtt
import time
import json
import os
from threading import Thread

# MQTT Configuration
MQTT_HOST = os.environ.get('MQTT_HOST', 'localhost')
MQTT_PORT = int(os.environ.get('MQTT_PORT', 8883))
MQTT_USER = os.environ.get('MQTT_USER')
MQTT_PASS = os.environ.get('MQTT_PASS')
MQTT_TOPIC_ID = os.environ.get('MQTT_TOPIC_ID', 'itsme').strip('/')
MQTT_TOPIC_START = os.environ.get('MQTT_TOPIC_START', 'v1').strip('/')
MQTT_SUB_TOPIC = '{}/req/{}/+/#'.format(MQTT_TOPIC_START, MQTT_TOPIC_ID)
MQTT_PUB_TOPIC = '{}/res/{}'.format(MQTT_TOPIC_START, MQTT_TOPIC_ID)
PATH_INDEX = MQTT_SUB_TOPIC.count('/')
VERB_INDEX = PATH_INDEX - 1

# HTTP Configuration
HTTP_BASE_URL = os.environ.get('HTTP_BASE_URL', 'http://localhost/').rstrip('/') + '/'
HTTP_USER = os.environ.get('HTTP_USER')
HTTP_PASS = os.environ.get('HTTP_PASS')
HTTP_AUTH = (HTTP_USER, HTTP_PASS) if HTTP_USER and HTTP_PASS else None

def on_connect(client, userdata, flags, rc):
    print("Connection successful: ", userdata, flags, rc)

def on_message(client, userdata, msg):
    print("Message received: ", msg.topic, msg.payload)
    Thread(target=_on_message, args=[client, userdata, msg]).start()

def _on_message(client, userdata, msg):
    topic_arr = msg.topic.split('/', PATH_INDEX)
    verb = topic_arr[VERB_INDEX]
    path = topic_arr[PATH_INDEX] if len(topic_arr) > PATH_INDEX else ''
    
    try:
        payload = json.loads(msg.payload)
    except ValueError:
        payload = None

    body_json = body_data = params = headers = req_id = None

    if type(payload) is dict:
        params = payload.get('params')
        body = payload.get('body')
        headers = payload.get('headers')
        req_id = payload.get('req_id')
        if type(body) is dict or type(body) is list:
            body_json = body
        else:
            body_data = body
        if type(headers) is not dict: headers = None

    r = requests.request(method=verb, url=HTTP_BASE_URL+path, params=params, data=body_data, json=body_json, auth=HTTP_AUTH)
    print(r.status_code, r.request.url)
    try:
        content = r.json()
    except ValueError:
        content = r.content.decode('utf-8')

    client.publish(topic='/'.join([MQTT_PUB_TOPIC,verb,path]).rstrip('/'), payload=json.dumps({'content': content, 'status': r.status_code, 'req_id': req_id}), qos=2)

client = mqtt.Client()
if MQTT_USER and MQTT_PASS:
    client.username_pw_set(username=MQTT_USER, password=MQTT_PASS)
client.connect(host=MQTT_HOST, port=MQTT_PORT)
client.subscribe(MQTT_SUB_TOPIC, qos=2)
client.on_connect = on_connect
client.on_message = on_message
client.loop_forever()