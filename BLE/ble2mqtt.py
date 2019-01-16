import socket
import time
import paho.mqtt.client as mqtt
from bluepy import btle
import binascii

connected = False
btconnected=False
m_temp = "0ºC"
m_rh = "0%"
m_aqi = "AQI: 0"

EvTH7271="fc:f4:35:bf:6b:37"
EvTH9640="e3:13:83:3a:33:c8"
EnvMultiUV0980="e7:7c:12:1f:73:24"

def main():
    global m_temp
    global m_rh
    global m_aqi
    global connected
    global btconnected


    h = socket.gethostname()+".local"
    lastTime = time.monotonic()
    getEnvInfoFromBLEDevices()
    ipaddr = socket.gethostbyname(h)
    while (True):
        thisTime = time.monotonic()
        if (thisTime - lastTime) > 300:
            lastTime = time.monotonic()
            getEnvInfoFromBLEDevices()
            ipaddr = socket.gethostbyname(h)


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    global connected

    connected = True
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe([("sensornet/env/home/balcony/temperature", 0), ("sensornet/env/home/balcony/humidity", 0), ("sensornet/env/home/living/aqi", 0)])

def on_disconnect(client, userdata, rc):
    global connected

    connected = False
    if rc != 0:
        print("Unexpected disconnection.")

def reverse(val):
    swb = bytearray(len(val))
    swb[0::2], swb[1::2] = val[1::2], val[0::2]
    return swb

def getEnvInfoFromBLEDevices():
    global m_temp
    global m_rh
    global btconnected

    gotdata = False
    error=False
    try:
#        devTH = btle.Peripheral(EnvMultiUV0980,btle.ADDR_TYPE_RANDOM)
#        devRH = btle.Peripheral(EvTH9640,btle.ADDR_TYPE_RANDOM)
        devRH = btle.Peripheral(EvTH7271,btle.ADDR_TYPE_RANDOM)
    except:
        error=True
        btconnected=False
        print("Cannot connect")

    if not error:
        btconnected=True
#        devTH.setMTU(31)
        devRH.setMTU(31)

        retry = 0
        while (not gotdata) and (retry < 4):
            envSensor = btle.UUID("0000181a-0000-1000-8000-00805f9b34fb")
            envTHSvc = devRH.getServiceByUUID(envSensor) 
            envRHSvc = devRH.getServiceByUUID(envSensor) 
            tempUUIDVal = btle.UUID("00002a6e-0000-1000-8000-00805f9b34fb")
            rhUUIDVal = btle.UUID("00002a6f-0000-1000-8000-00805f9b34fb")
            tempVal = envRHSvc.getCharacteristics(tempUUIDVal)[0]
            rhVal = envRHSvc.getCharacteristics(rhUUIDVal)[0]
            _tempB = tempVal.read()
            tempB = reverse(_tempB)
            _rhB = rhVal.read()
            rhB = reverse(_rhB)

            x = binascii.b2a_hex(tempB)
            y = binascii.b2a_hex(rhB)
            if (x != 0) and (y != 0):
                gotdata = True
                m_temp = str(round(int(x, 16)/100))+"ºC"
                m_rh = str(round(int(y,16)/100))+"%"
            else:
                retry += 1
        devRH.disconnect()
        print(time.strftime('%F %H:%M')+","+str(int(x, 16)/100.0)+","+str(int(y,16)/100.0))

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global m_aqi

#    print(msg.topic+" "+str(msg.payload))
    if (msg.topic == "sensornet/env/home/living/aqi"):
        x = str(msg.payload.decode("utf-8"))
        m_aqi = "AQI: "+str(round(float(x)))
    if (msg.topic == "sensornet/env/home/balcony/humidity"):
        x = str(msg.payload.decode("utf-8"))
#        m_rh = str(round(float(x)))+"%"

client = mqtt.Client()
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

client.connect_async("10.0.1.250", 1883, 60)

# Non-Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_start() #start loop to process received messages

if __name__ == '__main__':
    main()
