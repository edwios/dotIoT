#include "WiFi.h"
#include <ESP32HTTPUpdateServer.h>
#include <EspMQTTClient.h>
#include <ArduinoJson.h>
#include <gfxfont.h>
#include <Adafruit_GFX.h>
#include "Button2.h"
#include "esp_adc_cal.h"
#include "esp_system.h"

// include library, include base class, make path known
#include <GxEPD2.h>
#include "SD.h"
#include "SPI.h"
#include "secrets.h"

//! There are three versions of the 2.13 screen,
//  if you are not sure which version, please test each one,
//  if it is successful then it belongs to the model of the file name
//  关于v2.3版本的显示屏版本,如果不确定购买的显示屏型号,请每个头文件都测试一遍.

//include <GxGDE0213B1/GxGDE0213B1.h>      // 2.13" b/w
//#include <GxGDEH0213B72/GxGDEH0213B72.h>  // 2.13" b/w new panel
//#include <GxGDEH0213B73/GxGDEH0213B73.h>  // 2.13" b/w newer panel
//#include <epd/GxEPD2_213_B73.h>
#include <GxEPD2_BW.h>
//int bmpWidth = 150, bmpHeight = 39;
//width:150,height:39
// const unsigned char lilygo[] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0xf7, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x07, 0x31, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0f, 0xfc, 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0d, 0xfe, 0x60, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x19, 0xff, 0x20, 0x7f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x07, 0xf8, 0x0f, 0xf0, 0x00, 0xfe, 0x00, 0x03, 0xff, 0x80, 0x19, 0xe7, 0x30, 0x7f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x07, 0xfc, 0x0f, 0xf0, 0x07, 0xff, 0xc0, 0x0f, 0xff, 0xe0, 0x19, 0xe7, 0xb0, 0x7f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x03, 0xfc, 0x1f, 0xe0, 0x0f, 0xff, 0xe0, 0x1f, 0xff, 0xf8, 0x19, 0xff, 0x10, 0x7f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x03, 0xfe, 0x1f, 0xe0, 0x1f, 0xff, 0xf0, 0x3f, 0xff, 0xfc, 0x19, 0xff, 0x10, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x03, 0xfe, 0x1f, 0xc0, 0x3f, 0xff, 0xf0, 0x7f, 0xff, 0xfe, 0x19, 0xfe, 0x10, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x01, 0xfe, 0x3f, 0xc0, 0x7f, 0xff, 0xe0, 0x7f, 0xff, 0xfe, 0x19, 0xfe, 0x10, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x01, 0xff, 0x3f, 0x80, 0xff, 0xc7, 0xc0, 0xff, 0xff, 0xff, 0x1d, 0xfe, 0x10, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0xff, 0x7f, 0x80, 0xff, 0x81, 0x80, 0xff, 0xef, 0xff, 0x1d, 0xef, 0x00, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0xff, 0xff, 0x00, 0xff, 0x00, 0x00, 0xff, 0xc3, 0xff, 0x8f, 0xef, 0x00, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x7f, 0xff, 0x01, 0xff, 0x00, 0x01, 0xff, 0xc3, 0xff, 0x8f, 0x87, 0x80, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x7f, 0xfe, 0x01, 0xfe, 0x00, 0x01, 0xff, 0xc1, 0xff, 0x87, 0x81, 0xc0, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x7f, 0xfe, 0x01, 0xfe, 0x1f, 0x81, 0xff, 0x81, 0xff, 0x83, 0xff, 0x80, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x3f, 0xfc, 0x01, 0xfe, 0x3f, 0xf9, 0xff, 0x81, 0xff, 0x80, 0xfe, 0x00, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x3f, 0xfc, 0x01, 0xfe, 0x3f, 0xf9, 0xff, 0x81, 0xff, 0x80, 0x00, 0x00, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x1f, 0xf8, 0x01, 0xfe, 0x3f, 0xf9, 0xff, 0x81, 0xff, 0x80, 0x00, 0x00, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x1f, 0xf0, 0x01, 0xff, 0x3f, 0xf9, 0xff, 0xc1, 0xff, 0x80, 0x00, 0x00, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x0f, 0xf0, 0x01, 0xff, 0x3f, 0xf8, 0xff, 0xc1, 0xff, 0x80, 0x00, 0x00, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x0f, 0xf0, 0x00, 0xff, 0x9f, 0xf8, 0xff, 0xc1, 0xff, 0x80, 0x00, 0x00, 0x3f, 0xc0, 0x03, 0xfc, 0x7f, 0x80, 0x00, 0x0f, 0xf0, 0x00, 0xff, 0x83, 0xf0, 0xff, 0xe1, 0xff, 0x00, 0x00, 0x00, 0x3f, 0xfc, 0x03, 0xfc, 0x7f, 0xf8, 0x00, 0x0f, 0xf0, 0x00, 0xff, 0xe3, 0xf0, 0x7f, 0xff, 0xff, 0x00, 0x00, 0x00, 0x3f, 0xff, 0xe3, 0xfc, 0x7f, 0xff, 0xc0, 0x0f, 0xf0, 0x00, 0x7f, 0xff, 0xf0, 0x7f, 0xff, 0xfe, 0x00, 0x00, 0x00, 0x3f, 0xff, 0xe3, 0xfc, 0x7f, 0xff, 0xc0, 0x0f, 0xf0, 0x00, 0x7f, 0xff, 0xf0, 0x3f, 0xff, 0xfe, 0x00, 0x00, 0x00, 0x3f, 0xff, 0xe3, 0xfc, 0x7f, 0xff, 0xc0, 0x0f, 0xf0, 0x00, 0x3f, 0xff, 0xf0, 0x3f, 0xff, 0xfc, 0x00, 0x00, 0x00, 0x3f, 0xff, 0xe3, 0xfc, 0x7f, 0xff, 0xc0, 0x0f, 0xf0, 0x00, 0x1f, 0xff, 0xf0, 0x1f, 0xff, 0xfc, 0x00, 0x00, 0x00, 0x3f, 0xff, 0xe3, 0xf8, 0x7f, 0xff, 0xc0, 0x0f, 0xf0, 0x00, 0x0f, 0xff, 0xf0, 0x0f, 0xff, 0xf8, 0x00, 0x00, 0x00, 0x1f, 0xff, 0xc3, 0xf8, 0x1f, 0xff, 0xc0, 0x0f, 0xe0, 0x00, 0x03, 0xff, 0xe0, 0x03, 0xff, 0xe0, 0x00, 0x00, 0x00, 0x00, 0x3f, 0xc0, 0xf0, 0x00, 0x3f, 0x80, 0x07, 0xe0, 0x00, 0x00, 0xff, 0x80, 0x01, 0xff, 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3e, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};


// FreeFonts from Adafruit_GFX
#include <Fonts/FreeMonoBold9pt7b.h>
#include <Fonts/FreeSerif24pt7b.h>
#include <Fonts/FreeSans9pt7b.h>

//#include <GxIO/GxIO_SPI/GxIO_SPI.h>
//#include <GxIO/GxIO.h>

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

#define BUTTON_1            39
#define BUTTON_2            0

#define ADC_EN              14  //ADC_EN is the ADC detection enable port
#define ADC_PIN             35

//#define DEFAULT_LOCATION 0      // studyroom
#define DEFAULT_LOCATION 3    // outdoor

// Uncomment to print debug mesages
#define DEBUG

//GxIO_Class io(SPI, /*CS=5*/ ELINK_SS, /*DC=*/ ELINK_DC, /*RST=*/ ELINK_RESET);
//GxEPD_Class display(io, /*RST=*/ ELINK_RESET, /*BUSY=*/ ELINK_BUSY);
GxEPD2_BW<GxEPD2_213_B73, GxEPD2_213_B73::HEIGHT> display(GxEPD2_213_B73(/*CS=5*/ SS, /*DC=*/ 17, /*RST=*/ 16, /*BUSY=*/ 4)); // GDEH0213B73

//SPIClass sdSPI(VSPI);
Button2 btn1(BUTTON_1);
Button2 btn2(BUTTON_2);


const char *skuNum = "ioStation R&D";
bool sdOK = false;
bool dirty = false;
int startX = 40, startY = 10;
int btn1Cick = false;
int btn2Cick = false;
int vref = 1100;
char stemp[8];
char shumi[8];
char slux[12];
char datetime[20];
char sensorname[32];
char svolt[6];
int location_id = DEFAULT_LOCATION;
unsigned long last_epoch = millis();
const char *location;
const char * locations[] = {
    "studyroom",
    "livingroom",
    "masterbedroom",
    "outdoor",
    "hallway"
};
//const char *mac = WiFi.macAddress().c_str();

String getMacAddress() {
	uint8_t baseMac[6];
	// Get MAC address for WiFi station
	esp_read_mac(baseMac, ESP_MAC_WIFI_STA);
	char baseMacChr[18] = {0};
	sprintf(baseMacChr, "%02X%02X%02X%02X%02X%02X", baseMac[0], baseMac[1], baseMac[2], baseMac[3], baseMac[4], baseMac[5]);
	return String(baseMacChr);
}

String mac = getMacAddress();

static DynamicJsonDocument last_doc(2048);

EspMQTTClient client(
    SSID_NAME,
    SSID_PASS,
    MQTT_HOST,  // MQTT Broker server ip
    MQTT_USER,   // Can be omitted if not needed
    MQTT_PASS,   // Can be omitted if not needed
    mac.c_str()      // Client name that uniquely identify your device
);

void button_init()
{
    btn1.setLongClickHandler([](Button2 & b) {
        btn1Cick = false;
    });
    btn1.setPressedHandler([](Button2 & b) {
#ifdef DEBUG
        Serial.println("Button 1 clicked");
#endif
        btn1Cick = true;
        btn2Cick = false;
    });

    btn2.setPressedHandler([](Button2 & b) {
        btn1Cick = false;
#ifdef DEBUG
        Serial.println("Button 2 clicked");
#endif
        btn2Cick = true;
    });
}

void button_loop()
{
    btn1.loop();
    btn2.loop();
}

void showSkuNum()
{
    display.setCursor(10, display.height() - 4);
    display.print(skuNum);
}

void showVoltage()
{
//    static uint64_t timeStamp = 0;
//    if (millis() - timeStamp > 60000 || timeStamp == 0) {
//        timeStamp = millis();
        uint16_t v = analogRead(ADC_PIN);
        float battery_voltage = ((float)v / 4095.0) * 2.0 * 3.3 * (vref / 1000.0);
//        String voltage = String(battery_voltage) + "V";
//        Serial.println(voltage);
//        strcpy(svolt, voltage.c_str());
        sprintf(svolt, "%0.1fV", battery_voltage);
        int perc = int((battery_voltage - 3.0)/1.4*5.0+0.5);
        if (perc > 5) perc = 5;
        display.fillRect(8, 0, 72, 16, GxEPD_WHITE);
        display.setTextColor(GxEPD_BLACK);
        display.setFont(&FreeSans9pt7b);
        display.setCursor(12, 20);
//        display.print(svolt);
        display.print("[");
        display.setCursor(16, 22);
        for (int i = 0; i < 5; i++) {
            if (i < perc)
                display.print("/");
            else
                display.print(" ");
        }
        display.setCursor(42, 20);
        display.print("]");
//    }
}

void showConnection(bool forced)
{
    static uint8_t flip = 0;
//    static uint64_t timeStampC = 0;
//    if (millis() - timeStampC > 15000 || timeStampC == 0 || forced) {
//        timeStampC = millis();
/*
 * Only useful when diaplay can be updated in realtime
        if (flip) {
            flip = 0;
        } else {
            flip = 1;
        }
        if (flip) {
            display.fillRect(2, 4, 8, 16, GxEPD_BLACK);
            display.setTextColor(GxEPD_WHITE);
        } else {
            display.fillRect(2, 4, 8, 16, GxEPD_WHITE);
            display.setTextColor(GxEPD_BLACK);
        }
*/
        if (client.isConnected()) {
            display.setCursor(0, 16);
            display.setFont(&FreeSerif24pt7b);
            display.print(".");
        }
//    }
}


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
    if (strcmp(svolt, "") == 0) {
        sprintf(svolt, "%sV", "--");
    }
//    display.setPartialWindow(0, 0, display.width(), display.height() - 16);
    display.setFullWindow();
    display.fillRect(0, 0, display.width(), display.height(), GxEPD_WHITE);
    display.setTextColor(GxEPD_BLACK);
    display.setCursor(80, 16);
    display.setFont(&FreeMonoBold9pt7b);
    display.print(location);
//    display.setCursor(12, 10);
//    display.print(svolt);
    display.setFont(&FreeSerif24pt7b);
    display.setCursor(8, 64);
    display.print(stemp);
    display.setCursor(display.width() / 2, 60);
    display.print(shumi);

    display.setFont(&FreeMonoBold9pt7b);
    display.setCursor(8, 96);
    display.print(slux);

    showConnection(false);
    showVoltage();
    showSkuNum();
    display.display(false);
//    showConnection(true);
//    showVoltage();
}


void onConnectionEstablished() {
//    display.setPartialWindow(0, 0, display.width(), display.height());
#ifdef DEBUG
    Serial.println("MQTT connected");
#endif
/*
     display.fillRect(0, 0, display.width(), display.height() - 12, GxEPD_WHITE);
    display.setTextColor(GxEPD_BLACK);
    display.setCursor(2, 6);
    display.setFont(&FreeSerif24pt7b);
    display.println(".");
    display.setPartialWindow(0, 0, display.width(), display.height() - 12);
    updateDisplay();
*/

    if (location) {
        // Fill in last remembered data
        if (last_doc[location]) {
            float         temp     = last_doc[location]["readings"]["temperature"];
            float         humi     = last_doc[location]["readings"]["humidity"];
            unsigned long lux      = last_doc[location]["readings"]["lux"];
            const char   *dt       = last_doc[location]["datetime"];
            sprintf(stemp, "%0.1fC", temp);
            sprintf(shumi, "%d%%", int(humi));
            sprintf(slux, "%d lm", lux);
            strcpy(sensorname, location);
            strcpy(datetime, dt);
            dirty = true;
        }
    }
    client.subscribe("sensornet/env/+/status", [] (const String &payload)  {
#ifdef DEBUG
        Serial.println(payload);
#endif
        DynamicJsonDocument doc(1024);
        deserializeJson(doc, payload);
        const char* sensortype  = doc["type"];

        if (strncmp("environment", sensortype, 11*sizeof(char)) == 0) {
            const char *sensornm   = doc["device_name"];
#ifdef DEBUG
            Serial.print("DEBUG: <"); Serial.print(sensornm); Serial.println(">");
            Serial.print("DEBUG: <"); Serial.print(location); Serial.println(">");
#endif
            if (strncmp(location, sensornm, strlen(sensornm)) == 0) {
                last_doc[sensornm] = doc;
                float         temp     = doc["readings"]["temperature"];
                float         humi     = doc["readings"]["humidity"];
                unsigned long lux      = doc["readings"]["lux"];
                const char   *dt       = doc["datetime"];
                sprintf(stemp, "%0.1fC", temp);
                sprintf(shumi, "%d%%", int(humi));
                sprintf(slux, "%d lm", lux);
                strcpy(sensorname, sensornm);
                strcpy(datetime, dt);
                dirty = true;
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
const char* updatemode;

void setup()
{
    Serial.begin(115200);
#ifdef DEBUG
    Serial.println();
    Serial.println("Entered setup()");
    Serial.println(mac);
#endif
//    SPI.begin(SPI_CLK, SPI_MISO, SPI_MOSI, ELINK_SS);
    button_init();
    display.init(); // enable diagnostic output on Serial
//    client.enableDebuggingMessages();
 
    pinMode(ADC_EN, OUTPUT);
    digitalWrite(ADC_EN, HIGH);

    esp_adc_cal_characteristics_t adc_chars;
    esp_adc_cal_value_t val_type = esp_adc_cal_characterize((adc_unit_t)ADC_UNIT_1, (adc_atten_t)ADC1_CHANNEL_6, (adc_bits_width_t)ADC_WIDTH_BIT_12, 1100, &adc_chars);
    //Check type of calibration value used to characterize ADC
    if (val_type == ESP_ADC_CAL_VAL_EFUSE_VREF) {
#ifdef DEBUG
        Serial.printf("eFuse Vref:%u mV", adc_chars.vref);
#endif
        vref = adc_chars.vref;
    } else if (val_type == ESP_ADC_CAL_VAL_EFUSE_TP) {
        Serial.printf("Two Point --> coeff_a:%umV coeff_b:%umV\n", adc_chars.coeff_a, adc_chars.coeff_b);
    } else {
        Serial.print("Default Vref: 1100mV");
    }
#ifdef DEBUG
    Serial.println();
#endif

    display.setFullWindow();
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
    display.setCursor(140, display.height() - 2);
    if (sdOK) {
        uint32_t cardSize = SD.cardSize() / (1024 * 1024 * 1024);
        display.println(String(cardSize) + "GB SD");
    } else {
        display.println("No SD");
    }
#endif

    showSkuNum();
    display.display(false);

    client.setMaxPacketSize(320);       // Set max MQTT message + overhead size

    location = locations[location_id];
    updateDisplay();
#ifdef DEBUG
    Serial.print("Screen dimension: ");
    Serial.print(display.width());
    Serial.print("x");
    Serial.println(display.height());
#endif
    // goto sleep
//    esp_sleep_enable_ext0_wakeup((gpio_num_t)BUTTON_PIN, LOW);

//    esp_deep_sleep_start();
}


void loop()
{
    if (btn1Cick) {
        btn1Cick = false;
        // process button 1 click
        location_id++;
        if (location_id > 4) location_id = 0;
        location = locations[location_id];
        strcpy(sensorname, location);
#ifdef DEBUG
        Serial.print("Location changed to: <"); Serial.print(location); Serial.println(">");
#endif
        onConnectionEstablished();
        if (dirty) {
            dirty = false;
            updateDisplay();
        }
    }
    if (btn2Cick) {
        btn2Cick = false;
        // process button 2 click
    }
    button_loop();
    client.loop();
//    showVoltage();
//    showConnection(false);
}
