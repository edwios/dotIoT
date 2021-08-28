import time
from umqtt.robust import MQTTClient
import secrets
from machine import Pin, SoftSPI, ADC, RTC
import ssd1306
import config
import ujson
import ntptime
from writer import Writer
import largefont
import font6 as smallfont

DEBUG=False

m_all_devices = []
m_selected_device = None
m_selected_device_idx = 0
m_env_data = {}
m_has_update = False


def initNetwork(ssid, pwd):
    """Connect to Wi-Fi network with 10s timeout"""
    global DEBUG
    import network
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        # if DEBUG: print('connecting to network...')
        sta_if.active(True)
        time.sleep(0.5)
        sta_if.connect(ssid, pwd)
        lastTime = time.time()
        while (not sta_if.isconnected()) and ((time.time() - lastTime) < 10):
            pass
        if (time.time() >= lastTime + 10):
            WiFi_connected = False
            print("Error: timeout connecting to WLAN %s" % ssid)
        else:
            # if DEBUG: print("Connected to Wi-Fi")
            WiFi_connected = True
        if WiFi_connected and DEBUG: print('Wi-Fi connected, network config:', sta_if.ifconfig())
        return WiFi_connected
    return True


def initTouch():
    touch = Pin(config.TOUCH, Pin.IN)
    Pin(config.TOUCH_PWR, Pin.OUT, value=1)
    return touch


def powerOn():
    pwr_on=Pin(config.PWR_ON, Pin.OUT, value=1)


def initSPI():
    spi = SoftSPI(baudrate=config.BAUD, sck=Pin(config.SCK), mosi=Pin(config.MOSI), miso=Pin(config.MISO))
    return spi


def initDisplay(spi):
    dc=Pin(config.DC)
    rst=Pin(config.RST)
    cs=Pin(config.CS)
    oled_pwr = Pin(config.OLED_PWR, Pin.OUT, value=0)
    oled_pwr.value(1)
    display=ssd1306.SSD1306_SPI(config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT, spi, dc, rst, cs)
    return display


def initADC():
    adc = ADC(Pin(config.BATT_LVL))
    return adc


def readBatteryLevel(adc):
    adc.atten(ADC.ATTN_11DB)
    adc.width(ADC.WIDTH_9BIT)
    return adc.read()

def sub_cb(topic, msg):
    global m_env_data, m_selected_device, m_all_devices, m_has_update
    jobj = ujson.loads(str(msg, 'UTF-8'))
    device_name = None
    try:
        device_name = jobj['device_name']
        print(device_name)
    except:
        pass
    temp = None
    humi = None
    pres = None
    lux = None
    if device_name is not None:
        if device_name not in m_all_devices:
            m_all_devices.append(device_name)
        try:
            temp = str(round(jobj['readings']['temperature'], 1))
            humi = str(round(jobj['readings']['humidity'], 1))
            pres = str(round(jobj['readings']['pressure']))
            lux  = str(round(jobj['readings']['lux']))
        except:
            pass
        m_env_data.update({device_name: (temp, humi, pres, lux)})
        m_has_update = True


def initMQTT():
    topic = config.MQTT_TOPIC
    bTopic = bytes(topic, 'UTF-8')
    c = MQTTClient(config.MQTT_CLIENT_ID, config.MQTT_SERVER, user=secrets.MQTT_USER, password=secrets.MQTT_PASS)
    # Print diagnostic messages when retries/reconnects happens
    c.DEBUG = True
    c.set_callback(sub_cb)
    # Connect to server, requesting not to clean session for this
    # client. If there was no existing session (False return value
    # from connect() method), we perform the initial setup of client
    # session - subscribe to needed topics. Afterwards, these
    # subscriptions will be stored server-side, and will be persistent,
    # (as we use clean_session=False).
    #
    # There can be a problem when a session for a given client exists,
    # but doesn't have subscriptions a particular application expects.
    # In this case, a session needs to be cleaned first. See
    # example_reset_session.py for an obvious way how to do that.
    #
    # In an actual application, it's up to its developer how to
    # manage these issues. One extreme is to have external "provisioning"
    # phase, where initial session setup, and any further management of
    # a session, is done by external tools. This allows to save resources
    # on a small embedded device. Another extreme is to have an application
    # to perform auto-setup (e.g., clean session, then re-create session
    # on each restart). This example shows mid-line between these 2
    # approaches, where initial setup of session is done by application,
    # but if anything goes wrong, there's an external tool to clean session.
    if not c.connect(clean_session=True):
        print("New session being set up %s" % topic)
        c.subscribe(bTopic)
    else:
        print("Session already exist")
    return c


def print_status(display, hasnet, hasmqtt, hasupdate, batt_lvl):
    rtc = RTC()
    status = ' '
    if hasupdate:
        status = '*'
    if not hasnet:
        status = 'WiFi %s' % status
    if not hasmqtt:
        status = 'MQTT %s' % status
    (Y, M, D, h, m, s, W, ms) = time.localtime(time.mktime(time.localtime())+7200)
    datetime = '{:02d}:{:02d}'.format(h, m)
    batts = '%d%%' % (batt_lvl)
    if len(m_all_devices) > 0:
        display.text(m_all_devices[m_selected_device_idx], 0, 0, 1)
    display.fill_rect(0,0,127,16,0)
    display.text(m_selected_device, 0, 0, 1)
    display.fill_rect(0,48,127,16,0)
    display.text(batts, 0, 48, 1)
    wris = Writer(display, smallfont, verbose=False)
    wris.set_textpos(display, col = config.DISPLAY_WIDTH - wris.stringlen(datetime), row = 0)
    wris.printstring(datetime)
    wris.set_textpos(display, col = config.DISPLAY_WIDTH - wris.stringlen(status), row = 48)
    wris.printstring(status)
    display.show()


def main():
    global m_selected_device, m_selected_device_idx, m_all_devices, m_env_data, m_has_update
    mqtt_client = None
    hasNetwork = initNetwork(secrets.SSID, secrets.PASS)
    spi = initSPI()
    display = initDisplay(spi)
    wri = Writer(display, largefont, verbose=False)
    wris = Writer(display, smallfont, verbose=False)
    if hasNetwork:
        mqtt_client = initMQTT()
        ntptime.settime()
    powerOn()
    display.poweron()
    adc = initADC()
    batt_lvl = readBatteryLevel(adc)
    display.fill(0)
    wris.set_textpos(display, 0, 0)
    wris.printstring('Weather 1.0')
    if hasNetwork:
        display.text('WiFi', 0, 48, 1)
    if mqtt_client is not None:
        display.text('WiFi+MQTT', 0, 48, 1)
    display.show()
    time.sleep(2)
    was_touched = False
    virgin = True
    while 1:
        mc = False
        if mqtt_client is not None:
            mqtt_client.check_msg()
            # mc = mqtt_client.connect(clean_session=False)
            mc = True
        # Touch power overlapped with MISO, need to take SPI away fist
        SoftSPI.deinit(spi)
        touch = initTouch()
        time.sleep_ms(50)
        # We only act when finger lifted
        touched = (touch.value() == 1)
        released = (not touched and was_touched)
        was_touched = touched
        # We are done, SPI again
        spi = initSPI()
        if (released or virgin):
            if len(m_all_devices) > 0:
                if not virgin:
                    # First touch will not move pointer forward
                    m_selected_device_idx = m_selected_device_idx + 1
                    if m_selected_device_idx >= len(m_all_devices):
                        m_selected_device_idx = 0
                virgin = False  # Touched, no longer virgin
                m_selected_device = m_all_devices[m_selected_device_idx]
                m_has_update = False
        (temp, humi, pres, lux) = m_env_data[m_selected_device]
#            display.fill_rect(0, 0, 127, 16, 0)
        display.fill(0)
        display.text(m_selected_device, 0, 0, 1)
        if (config.STYLE == 0):
            if (temp is not None):
                display.text(temp, 8, 16, 1)
            if (humi is not None):
                display.text(humi, 64, 16, 1)
            if (pres is not None):
                display.text(pres, 8,32, 1)
            if (lux is not None):
                display.text(lux, 64, 32, 1)
        else:
            row = 20
            if (temp is not None):
                wri.set_textpos(display, col = 0, row = row)
                wri.printstring(str(temp)+' c')
            if (humi is not None):
                wri.set_textpos(display, col = config.DISPLAY_WIDTH - wri.stringlen('{:s}%'.format(humi)), row = row)
                wri.printstring('{:s}%'.format(humi))

        if batt_lvl != 0:
            batt_lvl = round((readBatteryLevel(adc)*140/512 + batt_lvl)/2)
        else:
            batt_lvl = round(readBatteryLevel(adc)*140/512)
        print_status(display, hasNetwork, mqtt_client is not None, m_has_update, batt_lvl)

    if mqtt_client is not None:
         mqtt_client.disconnect()


if __name__ == "__main__":
    main()

