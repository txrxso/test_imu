#include "certs.h" // root CA cert
#include "mqtt_config.h" // mqtt credentials
#include "secrets.h" // wifi credentials 

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <WiFi.h>
#include <WiFiClientSecure.h> // for TLS
#include <PubSubClient.h> // MQTT client


#define LOGGING_MODE 2 // 0: no logging, 1: log to Serial, 2: log to MQTT


WiFiClientSecure wifiClient;
PubSubClient mqttClient(wifiClient);
Adafruit_MPU6050 mpu;

unsigned long lastPublishMs = 0;

bool connectToMQTT(bool enableTLS = true) {
    Serial.print("WiFi status: ");
    Serial.println(WiFi.status() == WL_CONNECTED ? "Connected" : "Disconnected");

    bool success = false;

    if (enableTLS) {
        success = mqttClient.connect("ESP32Client", MQTT_USER, MQTT_PSWD);
    }
    else{
        success = mqttClient.connect("ESP32Client");
    }

    return success;
}

void connectToWifi() { 
    WiFi.mode(WIFI_STA);
    //WiFi.begin(HOTSPOT_SSID, HOTSPOT_PSWD);
    WiFi.begin(WIFI_SSID, WPA2_AUTH_PEAP, WIFI_EAP_ID, WIFI_USER, WIFI_PASSWORD);
    Serial.print("Connecting to WiFi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
}



void setup() { 
    Serial.begin(115200);

    if (!mpu.begin()) {
        Serial.println("Failed to find MPU6050 chip");
        while (1) {
            delay(100);
        }
    }

    mpu.setAccelerometerRange(MPU6050_RANGE_16_G);
    mpu.setGyroRange(MPU6050_RANGE_1000_DEG);
    mpu.setHighPassFilter(MPU6050_HIGHPASS_0_63_HZ);

    if (LOGGING_MODE == 2) {
        // set up wifi + mqttClient
        connectToWifi();
        wifiClient.setCACert(root_ca); // set root CA for TLS connection
        mqttClient.setServer(MQTT_SERVER_HIVEMQ_PRIVATE, MQTT_PORT_HIVEMQ_TLS);
        connectToMQTT();
    }


}


void loop() { 
    if (LOGGING_MODE == 2) {
        if (!mqttClient.connected()) {
            connectToMQTT(true);
        }
        mqttClient.loop();
    }

    unsigned long now = millis();
    if (now - lastPublishMs >= 10) {
        lastPublishMs = now;

        sensors_event_t accel, gyro, temp;
        mpu.getEvent(&accel, &gyro, &temp);

        if (LOGGING_MODE == 1) {
            Serial.print("{\"ts\":");
            Serial.print(now);
            Serial.print(",\"ax\":");
            Serial.print(accel.acceleration.x, 4);
            Serial.print(",\"ay\":");
            Serial.print(accel.acceleration.y, 4);
            Serial.print(",\"az\":");
            Serial.print(accel.acceleration.z, 4);
            Serial.print(",\"gx\":");
            Serial.print(gyro.gyro.x, 4);
            Serial.print(",\"gy\":");
            Serial.print(gyro.gyro.y, 4);
            Serial.print(",\"gz\":");
            Serial.print(gyro.gyro.z, 4);
            Serial.println("}");
            
        }
        else if (LOGGING_MODE == 2) {
            char payload[256];
            snprintf(
                payload,
                sizeof(payload),
                "{\"ts\":%lu,\"ax\":%.4f,\"ay\":%.4f,\"az\":%.4f,"
                "\"gx\":%.4f,\"gy\":%.4f,\"gz\":%.4f}",
                now,
                accel.acceleration.x,
                accel.acceleration.y,
                accel.acceleration.z,
                gyro.gyro.x,
                gyro.gyro.y,
                gyro.gyro.z
            );

            mqttClient.publish(MQTT_TOPIC_IMU_TEST, payload);
        }

    }

}