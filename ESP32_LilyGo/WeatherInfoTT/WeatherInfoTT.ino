#include <TFT_eSPI.h>
//#include <User_Setups/Setup25_TTGO_T_Display.h>
#include <SPI.h>
#include <WiFi.h>
#include <Wire.h>
#include "Button2.h"
#include "esp_adc_cal.h"
#include "bmp.h"
#include <EspMQTTClient.h>
#include <ArduinoJson.h>
#include "secrets.h"

#define ARRAY_SIZE(arr)     (sizeof(arr) / sizeof((arr)[0]))

#define DEFAULT_LOCATION 0      // studyroom
//#define DEFAULT_LOCATION 3    // outdoor

// TFT Pins has been set in the TFT_eSPI library in the User Setup file TTGO_T_Display.h
// #define TFT_MOSI            19
// #define TFT_SCLK            18
// #define TFT_CS              5
// #define TFT_DC              16
// #define TFT_RST             23
// #define TFT_BL              4   // Display backlight control pin


#define ADC_EN              14  //ADC_EN is the ADC detection enable port
#define ADC_PIN             34
#define BUTTON_1            35
#define BUTTON_2            0

#define AA_FONT_SMALL "NotoSansBold15"
#define AA_FONT_MONO  "NotoSansMonoSCB20" // NotoSansMono-SemiCondensedBold 20pt
#define AA_FONT_MONO_BIG "NotoSansBold36"
#define AA_FONT_MED "Final-Frontier-28"

TFT_eSPI tft = TFT_eSPI(135, 240); // Invoke custom library
Button2 btn1(BUTTON_1);
Button2 btn2(BUTTON_2);

bool lastConnected = false;
char buff[512];
int vref = 1100;
int btn1Cick = false;
int btn2Cick = false;
int uptodate = 0;
char stemp[28];
char slux[16];
char datetime[20];
uint16_t tcolour;
int rot = 1;
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
const char *mac = WiFi.macAddress().c_str();

EspMQTTClient client(
    SSID_NAME,
    SSID_PASS,
    MQTT_HOST,  // MQTT Broker server ip
    MQTT_USER,   // Can be omitted if not needed
    MQTT_PASS,   // Can be omitted if not needed
    mac      // Client name that uniquely identify your device
);

//Uncomment will use SDCard, this is just a demonstration,
//how to use the second SPI
//#define ENABLE_SPI_SDCARD

#ifdef ENABLE_SPI_SDCARD

#include "FS.h"
#include "SD.h"

SPIClass SDSPI(HSPI);

#define MY_CS       33
#define MY_SCLK     25
#define MY_MISO     27
#define MY_MOSI     26

void setupSDCard()
{
    SDSPI.begin(MY_SCLK, MY_MISO, MY_MOSI, MY_CS);
    //Assuming use of SPI SD card
    if (!SD.begin(MY_CS, SDSPI)) {
        Serial.println("Card Mount Failed");
        tft.setTextColor(TFT_RED);
        tft.drawString("SDCard Mount FAIL", tft.width() / 2, tft.height() / 2 - 32);
        tft.setTextColor(TFT_GREEN);
    } else {
        tft.setTextColor(TFT_GREEN);
        Serial.println("SDCard Mount PASS");
        tft.drawString("SDCard Mount PASS", tft.width() / 2, tft.height() / 2 - 48);
        String size = String((uint32_t)(SD.cardSize() / 1024 / 1024)) + "MB";
        tft.drawString(size, tft.width() / 2, tft.height() / 2 - 32);
    }
}
#else
#define setupSDCard()
#endif


void wifi_scan();

//! Long time delay, it is recommended to use shallow sleep, which can effectively reduce the current consumption
void espDelay(int ms)
{
    esp_sleep_enable_timer_wakeup(ms * 1000);
    esp_sleep_pd_config(ESP_PD_DOMAIN_RTC_PERIPH, ESP_PD_OPTION_ON);
    esp_light_sleep_start();
}

void showVoltage()
{
    static uint64_t timeStamp = 0;
    if (millis() - timeStamp > 1000) {
        timeStamp = millis();
        uint16_t v = analogRead(ADC_PIN);
        float battery_voltage = ((float)v / 4095.0) * 2.0 * 3.3 * (vref / 1000.0);
        String voltage = "Voltage :" + String(battery_voltage) + "V";
        Serial.println(voltage);
        tft.fillScreen(TFT_BLACK);
        tft.setTextDatum(MC_DATUM);
        tft.drawString(voltage,  tft.width() / 2, tft.height() / 2 );
    }
}

void button_init()
{
    btn1.setLongClickHandler([](Button2 & b) {
        btn1Cick = false;
        int r = digitalRead(TFT_BL);
        tft.fillScreen(TFT_BLACK);
        tft.setTextColor(TFT_GREEN, TFT_BLACK);
        tft.setTextDatum(MC_DATUM);
        tft.drawString("Press again to wake up",  tft.width() / 2, tft.height() / 2 );
        espDelay(6000);
        digitalWrite(TFT_BL, !r);

        tft.writecommand(TFT_DISPOFF);
        tft.writecommand(TFT_SLPIN);
        //After using light sleep, you need to disable timer wake, because here use external IO port to wake up
        esp_sleep_disable_wakeup_source(ESP_SLEEP_WAKEUP_TIMER);
        // esp_sleep_enable_ext1_wakeup(GPIO_SEL_35, ESP_EXT1_WAKEUP_ALL_LOW);
        esp_sleep_enable_ext0_wakeup(GPIO_NUM_35, 0);
        delay(200);
        esp_deep_sleep_start();
    });
    btn1.setPressedHandler([](Button2 & b) {
        Serial.println("Button 1 clicked");
        btn1Cick = true;
        btn2Cick = false;
    });

    btn2.setPressedHandler([](Button2 & b) {
        btn1Cick = false;
        Serial.println("Button 2 clicked");
        btn2Cick = true;
    });
}

void button_loop()
{
    btn1.loop();
    btn2.loop();
}

void wifi_scan()
{
    tft.setTextColor(TFT_GREEN, TFT_BLACK);
    tft.fillScreen(TFT_BLACK);
    tft.setTextDatum(MC_DATUM);
    tft.setTextSize(1);

    tft.drawString("ioStation R&D", tft.width() / 2, tft.height() / 2 - 20);
    tft.drawString("Scan Network", tft.width() / 2, tft.height() / 2);

    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    delay(100);

    int16_t n = WiFi.scanNetworks();
    tft.fillScreen(TFT_BLACK);
    if (n == 0) {
        tft.drawString("no networks found", tft.width() / 2, tft.height() / 2);
    } else {
        tft.setTextDatum(TL_DATUM);
        tft.setCursor(0, 0);
        Serial.printf("Found %d net\n", n);
        for (int i = 0; i < n; ++i) {
            sprintf(buff,
                    "[%d]:%s(%d)",
                    i + 1,
                    WiFi.SSID(i).c_str(),
                    WiFi.RSSI(i));
            tft.println(buff);
        }
    }
    // WiFi.mode(WIFI_OFF);
}

void drawLogo()
{
    tft.setRotation(rot);
    tft.fillScreen(TFT_BLACK);
    tft.setTextDatum(MC_DATUM);
    tft.setTextSize(1);
    tft.setTextColor(TFT_YELLOW);
    tft.drawString("ioStation R&D", tft.width() / 2, tft.height() / 2 + 60);
    if (client.isConnected()) {
        tft.setTextDatum(BL_DATUM);
        tft.setTextColor(TFT_GREEN);
        tft.drawString(".", 2, tft.height() - 2);
    } else if (client.isWifiConnected()){
        tft.setTextDatum(BL_DATUM);
        tft.setTextColor(TFT_YELLOW);
        tft.drawString(".", 2, tft.height() - 2);        
    } else if (client.isMqttConnected()){
        tft.setTextDatum(BL_DATUM);
        tft.setTextColor(TFT_ORANGE);
        tft.drawString(".", 2, tft.height() - 2);        
    }
}

void drawInfo() {
    if (strcmp(stemp, "") == 0) strcpy(stemp, "--C   --%rH");
    if (strcmp(slux, "") == 0) strcpy(slux, "-- lx");
    tft.setRotation(rot);
    tft.fillRect (0, 0, tft.width(),  tft.height() - 20, TFT_BLACK); // Overprint with a filled rectangle
    tft.fillRect (tft.width() - 60, tft.height() - 20, 60,  20, TFT_BLACK); // Overprint with a filled rectangle
    tft.fillRect (40, tft.height() / 2 + 18, tft.width() - 80,  20, tcolour); // Overprint with a filled rectangle
    tft.loadFont(AA_FONT_MED); // Must load the font first
    tft.setTextDatum(MC_DATUM);
    tft.setTextSize(1);
    tft.setTextColor(TFT_RED, TFT_BLACK);
    tft.drawString(location, tft.width() / 2, tft.height() / 2 - 50);
    tft.unloadFont(); // Remove the font to recover memory used
    tft.loadFont(AA_FONT_MONO_BIG); // Must load the font first
    tft.setTextDatum(MC_DATUM);
    tft.setTextSize(1);
    tft.setTextColor(TFT_GREEN, TFT_BLACK);
    tft.drawString(stemp, tft.width() / 2, tft.height() / 2 - 8);
    tft.unloadFont(); // Remove the font to recover memory used
    tft.setTextDatum(MR_DATUM);
    tft.setTextSize(2);
    tft.setTextColor(TFT_ORANGE, TFT_BLACK);    
    tft.drawString(slux, tft.width(), tft.height() / 2 + 54);
}

void onConnectionEstablished() {
    Serial.println("Connected");
    client.subscribe("sensornet/env/+/status", [] (const String &payload)  {
        Serial.println(payload);
        DynamicJsonDocument doc(1024);
        deserializeJson(doc, payload);
        const char* sensortype  = doc["type"];

        if (strncmp("environment", sensortype, 11*sizeof(char)) == 0) {
            const char *sensornm   = doc["device_name"];
            if (strcmp(location, sensornm) == 0) {
                float         temp     = doc["readings"]["temperature"];
                float         humi     = doc["readings"]["humidity"];
                sprintf(stemp, "%0.1fC   %0.0f%%", temp, humi);
                if (temp < 20.0)
                    tcolour = TFT_BLUE;
                else if (temp < 22.0)
                    tcolour = TFT_CYAN;
                else if (temp < 25.0)
                    tcolour = TFT_GREEN;
                else if (temp < 26.0)
                    tcolour = TFT_YELLOW;
                else
                    tcolour = TFT_RED;
                unsigned long lux      = doc["readings"]["lux"];
                sprintf(slux, "%d lx", lux);
                const char   *dt       = doc["datetime"];
                strcpy(datetime, dt);

                drawInfo();
            }
        }
    });

//  client.publish("mytopic/test", "This is a message");
}

void setup()
{
    Serial.begin(115200);
    Serial.println("Start");

    if (!SPIFFS.begin()) {
      Serial.println("SPIFFS initialisation failed!");
      while (1) yield(); // Stay here twiddling thumbs waiting
    }
    Serial.println("\r\nSPIFFS available!");
    
    // ESP32 will crash if any of the fonts are missing
    bool font_missing = false;
    if (SPIFFS.exists("/NotoSansBold15.vlw")    == false) font_missing = true;
    if (SPIFFS.exists("/NotoSansMonoSCB20.vlw")    == false) font_missing = true;
    if (SPIFFS.exists("/NotoSansBold36.vlw")    == false) font_missing = true;
    if (SPIFFS.exists("/Final-Frontier-28.vlw")    == false) font_missing = true;
  
    if (font_missing)
    {
      Serial.println("\r\nFont missing in SPIFFS, did you upload it?");
      while(1) yield();
    }
    else Serial.println("\r\nFonts found OK.");

    /*
    ADC_EN is the ADC detection enable port
    If the USB port is used for power supply, it is turned on by default.
    If it is powered by battery, it needs to be set to high level
    */
    pinMode(ADC_EN, OUTPUT);
    digitalWrite(ADC_EN, HIGH);

    tft.init();
    tft.setRotation(1);
    tft.fillScreen(TFT_BLACK);
    tft.setTextSize(2);
    tft.setTextColor(TFT_GREEN);
    tft.setCursor(0, 0);
    tft.setTextDatum(MC_DATUM);
    tft.setTextSize(1);

    /*
    if (TFT_BL > 0) {                           // TFT_BL has been set in the TFT_eSPI library in the User Setup file TTGO_T_Display.h
        pinMode(TFT_BL, OUTPUT);                // Set backlight pin to output mode
        digitalWrite(TFT_BL, TFT_BACKLIGHT_ON); // Turn backlight on. TFT_BACKLIGHT_ON has been set in the TFT_eSPI library in the User Setup file TTGO_T_Display.h
    }
    */

    tft.setSwapBytes(true);
    tft.pushImage(0, 0,  240, 135, ttgo);
    espDelay(1000);


    tft.setRotation(0);
    tft.fillScreen(TFT_RED);
    espDelay(500);
    tft.fillScreen(TFT_BLUE);
    espDelay(500);
    tft.fillScreen(TFT_GREEN);
    espDelay(500);

    tft.setRotation(1);

    button_init();

    esp_adc_cal_characteristics_t adc_chars;
    esp_adc_cal_value_t val_type = esp_adc_cal_characterize((adc_unit_t)ADC_UNIT_1, (adc_atten_t)ADC1_CHANNEL_6, (adc_bits_width_t)ADC_WIDTH_BIT_12, 1100, &adc_chars);
    //Check type of calibration value used to characterize ADC
    if (val_type == ESP_ADC_CAL_VAL_EFUSE_VREF) {
        Serial.printf("eFuse Vref:%u mV", adc_chars.vref);
        vref = adc_chars.vref;
    } else if (val_type == ESP_ADC_CAL_VAL_EFUSE_TP) {
        Serial.printf("Two Point --> coeff_a:%umV coeff_b:%umV\n", adc_chars.coeff_a, adc_chars.coeff_b);
    } else {
        Serial.println("Default Vref: 1100mV");
    }

 //   setupSDCard();

    location = locations[location_id];
    drawLogo();
    drawInfo();
    
/*    tft.setTextColor(TFT_GREEN, TFT_BLACK);
    tft.drawString("LeftButton:", tft.width() / 2, tft.height() / 2 - 16);
    tft.drawString("[WiFi Scan]", tft.width() / 2, tft.height() / 2 );
    tft.drawString("RightButton:", tft.width() / 2, tft.height() / 2 + 16);
    tft.drawString("[Voltage Monitor]", tft.width() / 2, tft.height() / 2 + 32 );
    tft.drawString("RightButtonLongPress:", tft.width() / 2, tft.height() / 2 + 48);
    tft.drawString("[Deep Sleep]", tft.width() / 2, tft.height() / 2 + 64 );
*/
}

void loop()
{
    if (btn1Cick) {
        btn1Cick = false;
        if (rot == 3)
            rot = 1;
        else
            rot = 3;
        drawLogo();
        drawInfo();
    }
    if (btn2Cick) {
        btn2Cick = false;
        location_id++;
        if (location_id > 4) location_id = 0;
        location = locations[location_id];
//        drawLogo();
        drawInfo();
    }
    button_loop();
    client.loop();
    if (client.isConnected() != lastConnected) {
        lastConnected = client.isConnected();
        drawLogo();
        drawInfo();
    }
}
