#!/usr/bin/env python

# telldussense.py
# Monitor 433 incoming on a TellStick
# Used for motion sensor trigger detection
# Also can be adapted to monitor other 433MHz sensors

import socket
import sys
import time
import json
import paho.mqtt.client as mqtt
import secrets
from argparse import ArgumentParser


DEBUG = True

MQTT_PUB_TOPIC_STATUS = 'sensornet/env/{:s}/status'
MQTT_PUB_TOPIC_AVAIL = 'sensornet/env/{:s}/availability'
MQTT_USER = secrets.MQTT_USER
MQTT_PASS = secrets.MQTT_PASS

m_connected = False


def on_connect(client, userdata, flags, rc):
    global m_connected, DEBUG
    m_connected = True
    if DEBUG: print("%s Debug: MQTT broker connected" % time.strftime('%F %H:%M:%S'))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    #    client.subscribe([("sensornet/env/home/balcony/temperature", 0), ("sensornet/env/home/balcony/humidity", 0), ("sensornet/env/home/living/aqi", 0)])
    # client.subscribe([("sensornet/env/balcony/brightness", 0), ("sensornet/all", 0), ("sensornet/command", 0)])


def on_disconnect(client, userdata, rc):
    global m_connected, DEBUG
    m_connected = False
    if rc != 0:
        print("%s INFO: MQTT broker disconnected, will not try agian" % time.strftime('%F %H:%M:%S'))


def on_publish(client, userdata, result):
    pass


# The callback for when a PUBLISH message is received from the broker.
def on_message(client, userdata, msg):
    pass


def mqttinit(mqtthub, port, user, passwd):
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    if DEBUG: print("%s DEBUG: Connecting to mqtt host %s" % (time.strftime('%F %H:%M:%S'), mqtthub))
    client.username_pw_set(username=user, password=passwd)
    client.connect_async(mqtthub, port, 60)
    client.loop_start() #start loop to process received messages
    return client


def get_args():
    arg_parser = ArgumentParser(description="Motion MQTT")
    arg_parser.add_argument("-i", "--interval", help="Monitoring interval", default=900)
    arg_parser.add_argument("-c", "--offdelay", help="Delay in s to send OFF state", default=0)
    arg_parser.add_argument("-t", "--tellstick", help="IP address of TellStick", default='10.0.1.2')
    arg_parser.add_argument("-n", "--name", help="Name of device", default='livingroom_motion')    
    arg_parser.add_argument("-d", "--debug", help="Debug", action='store_true')
    arg_parser.add_argument("-H", "--mqtt", help="MQTT broker address ", default='10.0.1.250')
    args = arg_parser.parse_args()
    return args


def initTellStick(ip, port):
    # Create socket for server
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)

    # Let's send data through UDP protocol
    send_data = 'B:reglistener'
    s.sendto(send_data.encode('utf-8'), (ip, port))
    return s


def publishState(mclient, mtopic, devname, state, usejson=True):
    if mclient is None or not m_connected:
        print("Error! MQTT broker not connected")
        return
    if usejson:
        if state is None or state == '':
            state = 'ON'
        mesg = {}
        mesg['state'] = state
        mesg['device_name'] = devname
        dt = time.strftime('%F %H:%M:%S')
        mesg['datetime'] = dt
        mesg['type'] = 'trigger'
        jstr = json.dumps(mesg)
    else:
        jstr = state
    if mclient:
        mclient.publish(mtopic, jstr, retain=False)


def main():
    global DEBUG
    global m_connected, MQTT_USER, MQTT_PASS

    args = get_args()
    ip = args.tellstick
    devname = args.name
    port = 42314
    mqtthost = args.mqtt
    stateOn = True
    udpsocket = None
    mtopic = MQTT_PUB_TOPIC_STATUS.format(devname)
    atopic = MQTT_PUB_TOPIC_AVAIL.format(devname)

    while not m_connected:
        time.sleep(5)
        if not m_connected:
            mqttclient = mqttinit(mqtthost, 1883, MQTT_USER, MQTT_PASS)

    while udpsocket is None:
        try:
            udpsocket = initTellStick(ip, port)
        except:
            print("Error! Cannot initialise UDP to TellStick")
            time.sleep(10)
            continue
        else:
            print("Online")
            publishState(mqttclient, atopic, devname, 'online', usejson=False)
        lt = time.monotonic()
        cnt = 0
        debounce = False

        while True:
            try:
                data, address = udpsocket.recvfrom(4096)
            except:
                udpsocket.close()
                udpsocket = None
                break
            recvstr = data.decode('utf-8')
            # print("\n\n 2. Client received : ", recvstr, "\n\n")
            if time.monotonic() - lt > 5 or cnt == 0:
                if debounce:
                    debounce = False
                cnt = 0
                lt = time.monotonic()
            if '12781' in recvstr:
                cnt = cnt + 1
            if cnt > 3 and not debounce:
                print("Motion detected")
                publishState(mqttclient, mtopic, devname, 'ON')
                stateOn = True
                debounce = True
        if (not m_connected):
            mqttclient = mqttinit(mqtthost, 1883, MQTT_USER, MQTT_PASS)
        publishState(mqttclient, atopic, devname, 'offline', usejson=False)



if __name__ == "__main__":
    main()
