#include "WiFi.h"
#include <ESP32HTTPUpdateServer.h>
#include <EspMQTTClient.h>
#include <ArduinoJson.h>
#include <gfxfont.h>
#include <Adafruit_GFX.h>

// include library, include base class, make path known
#include <GxEPD.h>
#include "SD.h"
#include "SPI.h"
#include "secrets.h"

//! There are three versions of the 2.13 screen,
//  if you are not sure which version, please test each one,
//  if it is successful then it belongs to the model of the file name
//  关于v2.3版本的显示屏版本,如果不确定购买的显示屏型号,请每个头文件都测试一遍.

//include <GxGDE0213B1/GxGDE0213B1.h>      // 2.13" b/w
//#include <GxGDEH0213B72/GxGDEH0213B72.h>  // 2.13" b/w new panel
#include <GxGDEH0213B73/GxGDEH0213B73.h>  // 2.13" b/w newer panel

//int bmpWidth = 150, bmpHeight = 39;
//width:150,height:39
// const unsigned char lilygo[] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0xf7, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x07, 0x31, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0f, 0xfc, 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0d, 0xfe, 0x60, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x19, 0xff, 0x20, 0x7f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x07, 0xf8, 0x0f, 0xf0, 0x00, 0xfe, 0x00, 0x03, 0xff, 0x80, 0x19, 0xe7, 0x30, 0x7f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x07, 0xfc, 0x0f, 0xf0, 0x07, 0xff, 0xc0, 0x0f, 0xff, 0xe0, 0x19, 0xe7, 0xb0, 0x7f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x03, 0xfc, 0x1f, 0xe0, 0x0f, 0xff, 0xe0, 0x1f, 0xff, 0xf8, 0x19, 0xff, 0x10, 0x7f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x03, 0xfe, 0x1f, 0xe0, 0x1f, 0xff, 0xf0, 0x3f, 0xff, 0xfc, 0x19, 0xff, 0x10, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x03, 0xfe, 0x1f, 0xc0, 0x3f, 0xff, 0xf0, 0x7f, 0xff, 0xfe, 0x19, 0xfe, 0x10, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x01, 0xfe, 0x3f, 0xc0, 0x7f, 0xff, 0xe0, 0x7f, 0xff, 0xfe, 0x19, 0xfe, 0x10, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x01, 0xff, 0x3f, 0x80, 0xff, 0xc7, 0xc0, 0xff, 0xff, 0xff, 0x1d, 0xfe, 0x10, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0xff, 0x7f, 0x80, 0xff, 0x81, 0x80, 0xff, 0xef, 0xff, 0x1d, 0xef, 0x00, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0xff, 0xff, 0x00, 0xff, 0x00, 0x00, 0xff, 0xc3, 0xff, 0x8f, 0xef, 0x00, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x7f, 0xff, 0x01, 0xff, 0x00, 0x01, 0xff, 0xc3, 0xff, 0x8f, 0x87, 0x80, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x7f, 0xfe, 0x01, 0xfe, 0x00, 0x01, 0xff, 0xc1, 0xff, 0x87, 0x81, 0xc0, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x7f, 0xfe, 0x01, 0xfe, 0x1f, 0x81, 0xff, 0x81, 0xff, 0x83, 0xff, 0x80, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x3f, 0xfc, 0x01, 0xfe, 0x3f, 0xf9, 0xff, 0x81, 0xff, 0x80, 0xfe, 0x00, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x3f, 0xfc, 0x01, 0xfe, 0x3f, 0xf9, 0xff, 0x81, 0xff, 0x80, 0x00, 0x00, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x1f, 0xf8, 0x01, 0xfe, 0x3f, 0xf9, 0xff, 0x81, 0xff, 0x80, 0x00, 0x00, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x1f, 0xf0, 0x01, 0xff, 0x3f, 0xf9, 0xff, 0xc1, 0xff, 0x80, 0x00, 0x00, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x0f, 0xf0, 0x01, 0xff, 0x3f, 0xf8, 0xff, 0xc1, 0xff, 0x80, 0x00, 0x00, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x0f, 0xf0, 0x00, 0xff, 0x9f, 0xf8, 0xff, 0xc1, 0xff, 0x80, 0x00, 0x00, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x0f, 0xf0, 0x00, 0xff, 0x83, 0xf0, 0xff, 0xe1, 0xff, 0x00, 0x00, 0x00, 0x3f, 0xfc, 0x03, 0xfc, 0x7f, 0xf8, 0x00, 0x0f, 0xf0, 0x00, 0xff, 0xe3, 0xf0, 0x7f, 0xff, 0xff, 0x00, 0x00, 0x00, 0x3f, 0xff, 0xe3, 0xfc, 0x7f, 0xff, 0xc0, 0x0f, 0xf0, 0x00, 0x7f, 0xff, 0xf0, 0x7f, 0xff, 0xfe, 0x00, 0x00, 0x00, 0x3f, 0xff, 0xe3, 0xfc, 0x7f, 0xff, 0xc0, 0x0f, 0xf0, 0x00, 0x7f, 0xff, 0xf0, 0x3f, 0xff, 0xfe, 0x00, 0x00, 0x00, 0x3f, 0xff, 0xe3, 0xfc, 0x7f, 0xff, 0xc0, 0x0f, 0xf0, 0x00, 0x3f, 0xff, 0xf0, 0x3f, 0xff, 0xfc, 0x00, 0x00, 0x00, 0x3f, 0xff, 0xe3, 0xfc, 0x7f, 0xff, 0xc0, 0x0f, 0xf0, 0x00, 0x1f, 0xff, 0xf0, 0x1f, 0xff, 0xfc, 0x00, 0x00, 0x00, 0x3f, 0xff, 0xe3, 0xf8, 0x7f, 0xff, 0xc0, 0x0f, 0xf0, 0x00, 0x0f, 0xff, 0xf0, 0x0f, 0xff, 0xf8, 0x00, 0x00, 0x00, 0x1f, 0xff, 0xc3, 0xf8, 0x1f, 0xff, 0xc0, 0x0f, 0xe0, 0x00, 0x03, 0xff, 0xe0, 0x03, 0xff, 0xe0, 0x00, 0x00, 0x00, 0x00, 0x3f, 0xc0, 0xf0, 0x00, 0x3f, 0x80, 0x07, 0xe0, 0x00, 0x00, 0xff, 0x80, 0x01, 0xff, 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3e, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};


// FreeFonts from Adafruit_GFX
#include <Fonts/FreeMonoBold9pt7b.h>
#include <Fonts/FreeMonoBold12pt7b.h>
#include <Fonts/FreeMonoBold18pt7b.h>
#include <Fonts/FreeSerif24pt7b.h>


#include <GxIO/GxIO_SPI/GxIO_SPI.h>
#include <GxIO/GxIO.h>

#define SPI_MOSI 23
#define SPI_MISO -1
#define SPI_CLK 18

#define ELINK_SS 5
#define ELINK_BUSY 4
#define ELINK_RESET 16
#define ELINK_DC 17

#define SDCARD_SS 13
#define SDCARD_CLK 14
#define SDCARD_MOSI 15
#define SDCARD_MISO 2

#define BUTTON_PIN 39

//#define LOCATION_ID "livingroom"
#define LOCATION_ID "outdoor"


GxIO_Class io(SPI, /*CS=5*/ ELINK_SS, /*DC=*/ ELINK_DC, /*RST=*/ ELINK_RESET);
GxEPD_Class display(io, /*RST=*/ ELINK_RESET, /*BUSY=*/ ELINK_BUSY);

SPIClass sdSPI(VSPI);


const char *skuNum = "ioStation R&D";
bool sdOK = false;
int startX = 40, startY = 10;
char stemp[8];
char shumi[8];
char slux[12];
char datetime[20];
char sensorname[32];


EspMQTTClient client(
    SSID_NAME,
    SSID_PASS,
    MQTT_HOST,  // MQTT Broker server ip
    MQTT_USER,   // Can be omitted if not needed
    MQTT_PASS,   // Can be omitted if not needed
    "WS04"      // Client name that uniquely identify your device
);


void updateDisplay() {
    if (strcmp(stemp, "") == 0) {
        sprintf(stemp, "%0.1fC %d%%", 99.9, int(100));
    }
    if (strcmp(slux, "") == 0) {
        sprintf(slux, "Lux:%d lm", 29999);
    }
    if (strcmp(sensorname, "") == 0) {
        sprintf(sensorname, "%s", "No sensor");
    }
    display.fillRect(0, 0, display.width(), display.height() - 12, GxEPD_WHITE);
    display.setTextColor(GxEPD_BLACK);
    display.setCursor(80, 10);
    display.setFont(&FreeMonoBold9pt7b);
    display.println(sensorname);

    display.setFont(&FreeSerif24pt7b);
    display.setCursor(5, 60);
    display.println(stemp);
    display.setCursor(display.width() / 2, 60);
    display.println(shumi);

    display.setFont(&FreeMonoBold9pt7b);
    display.setCursor(5, 90);
    display.println(slux);

    if (client.isConnected()) {
        display.setCursor(2, 6);
        display.setFont(&FreeSerif24pt7b);
        display.println(".");
    }

    display.updateWindow(0, 0, display.width(), display.height() - 12, true);
}


void onConnectionEstablished() {
    display.updateWindow(0, 0, display.width(), display.height(), false);
    Serial.println("MQTT connected");
    display.fillRect(0, 0, display.width(), display.height() - 12, GxEPD_WHITE);
    display.setTextColor(GxEPD_BLACK);
    display.setCursor(2, 6);
    display.setFont(&FreeSerif24pt7b);
    display.println(".");
    display.updateWindow(0, 0, display.width(), display.height() - 12, true);
    updateDisplay();
    client.subscribe("sensornet/env/+/status", [] (const String &payload)  {
        Serial.println(payload);
        DynamicJsonDocument doc(1024);
        deserializeJson(doc, payload);
        const char* sensortype  = doc["type"];

        if (strncmp("environment", sensortype, 11*sizeof(char)) == 0) {
            const char *sensornm   = doc["device_name"];
            if (strcmp(LOCATION_ID, sensornm) == 0) {
                float         temp     = doc["readings"]["temperature"];
                float         humi     = doc["readings"]["humidity"];
                unsigned long lux      = doc["readings"]["lux"];
                const char   *dt       = doc["datetime"];
                sprintf(stemp, "%0.1fC", temp);
                sprintf(shumi, "%d%%", int(humi));
                sprintf(slux, "%d lm", lux);
                strcpy(sensorname, sensornm);
                strcpy(datetime, dt);
                updateDisplay();
            }
        }
  });

//  client.publish("mytopic/test", "This is a message");
}

/* 
void wifiscan()
{
    char buff[512];

    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    delay(100);

    int16_t n = WiFi.scanNetworks();
    if (n == 0) {
        Serial.println("no networks found");
    } else {
        Serial.printf("Found %d net\n", n);
        for (int i = 0; i < n; ++i) {
            sprintf(buff,
                    "[%d]:%s(%d)",
                    i + 1,
                    WiFi.SSID(i).c_str(),
                    WiFi.RSSI(i));
            Serial.println(buff);
        }
    }
}
 */

void setup()
{
    Serial.begin(115200);
    Serial.println();
    Serial.println("setup");
    SPI.begin(SPI_CLK, SPI_MISO, SPI_MOSI, ELINK_SS);
    display.init(); // enable diagnostic output on Serial
//    client.enableDebuggingMessages();

    display.setRotation(1);
    display.fillScreen(GxEPD_WHITE);
    display.setTextColor(GxEPD_BLACK);
    display.setFont(&FreeMonoBold9pt7b);
    display.setCursor(0, 0);

#ifdef USE_SD
    sdSPI.begin(SDCARD_CLK, SDCARD_MISO, SDCARD_MOSI, SDCARD_SS);

    if (!SD.begin(SDCARD_SS, sdSPI)) {
        sdOK = false;
    } else {
        sdOK = true;
    }
#endif

    display.fillScreen(GxEPD_WHITE);

    display.setCursor(10, display.height() - 2);
    display.println(skuNum);

#ifdef USE_SD
    if (sdOK) {
        uint32_t cardSize = SD.cardSize() / (1024 * 1024);
        display.println(String(cardSize) + "MB SD");
    } else {
        display.println("No SD");
    }
#endif

    display.update();

    Serial.println(display.width());
    Serial.println(display.height());
    // goto sleep
//    esp_sleep_enable_ext0_wakeup((gpio_num_t)BUTTON_PIN, LOW);

//    esp_deep_sleep_start();
}


void loop()
{
    client.loop();
}
