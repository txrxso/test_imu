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
#define COLLECTION_TYPE 1 // 0: collect both accel and gyro, 1: including fall/impact detection states

WiFiClientSecure wifiClient;
PubSubClient mqttClient(wifiClient);
Adafruit_MPU6050 mpu;

unsigned long lastPublishMs = 0;

#if COLLECTION_TYPE == 1
// ============================================
// THRESHOLDS AND PARAMETERS AND OTHER STATES
// ============================================
#define SEVERE_IMPACT_THRESHOLD_G 8.0
#define MEDIUM_IMPACT_THRESHOLD_G 4.0
#define FREEFALL_THRESHOLD_G 0.3
#define JERK_THRESHOLD_G_PER_S 65.0
#define MOTIONLESS_ACC_THRESHOLD 0.3
#define ROTATION_THRESHOLD_DEG_S 200.0
#define MOTIONLESS_GYRO_THRESHOLD_DEG_S 20.0

#define MIN_FREEFALL_DURATION_MS 100
#define MAX_FREEFALL_TO_IMPACT_MS 500
#define POST_IMPACT_OBS_DURATION_MS 200
#define MOTIONLESS_THRESHOLD_MS 2000

#define WINDOW_SIZE 3
#define SUSTAINED_THRESHOLD 2

// ============================================
// ENUMS
// ============================================
enum class SafetyEvent {
  NONE = 0,
  FALL = 1,
  DIRECT_IMPACT = 2,
  HEAVY_IMPACT = 3
};

enum class InternalSafetyState {
  NORMAL = 0,
  FREEFALL = 1,
  IMPACT = 2,
  POST_IMPACT = 3,
  INJURY_LIKELY = 4,
  RECOVERED = 5
};

// ============================================
// STATE STRUCTURES
// ============================================
struct InternalDetectionState {
  InternalSafetyState currentState;
  SafetyEvent detectedEvent;
  
  uint32_t freefallStartTime;
  uint32_t impactStartTime;
  uint32_t motionlessStartTime;
  
  float prevResultantAcc;
  uint32_t prevAccTime;
  float prev2ResultantAcc;
  uint32_t prev2AccTime;
  float prev3ResultantAcc;
  uint32_t prev3AccTime;
  
  float preEventOrientation[3];
};

struct IMUData {
  float accX, accY, accZ;
  float gyroX, gyroY, gyroZ;
  float resultant_acc;
  float resultant_gyro;
};


InternalDetectionState detectionState;
float accelWindow[WINDOW_SIZE];
float gyroWindow[WINDOW_SIZE];
int windowIndex = 0;


// ============================================
// HELPER FUNCTIONS
// ============================================
float getResultant(float x, float y, float z) {
  return sqrt(x * x + y * y + z * z);
}

float getJerk(float sample1, float sample2, float timeDelta_sec) {
  if (timeDelta_sec <= 0) return 0;
  return (sample2 - sample1) / timeDelta_sec;
}

float calcJerk(InternalDetectionState &d, float currentAcc, uint32_t currentTime) {
  float dt1 = (currentTime - d.prevAccTime) / 1000.0;
  float dt2 = (d.prevAccTime - d.prev2AccTime) / 1000.0;
  float dt3 = (d.prev2AccTime - d.prev3AccTime) / 1000.0;
  
  if (dt1 <= 0) dt1 = 0.01;
  if (dt2 <= 0) dt2 = 0.01;
  if (dt3 <= 0) dt3 = 0.01;
  
  float jerk1 = getJerk(d.prevResultantAcc, currentAcc, dt1);
  float jerk2 = getJerk(d.prev2ResultantAcc, d.prevResultantAcc, dt2);
  float jerk3 = getJerk(d.prev3ResultantAcc, d.prev2ResultantAcc, dt3);
  
  return (abs(jerk1) + abs(jerk2) + abs(jerk3)) / 3.0;
}

void updateJerkHistory(InternalDetectionState &d, float currentAcc, uint32_t currentTime) {
  d.prev3ResultantAcc = d.prev2ResultantAcc;
  d.prev3AccTime = d.prev2AccTime;
  d.prev2ResultantAcc = d.prevResultantAcc;
  d.prev2AccTime = d.prevAccTime;
  d.prevResultantAcc = currentAcc;
  d.prevAccTime = currentTime;
}

bool checkPostImpactOrientation(float ax, float ay, float az) {
  float horizontal_acc = sqrt(ax*ax + ay*ay);
  float vertical_acc = abs(az);
  return (horizontal_acc > 0.7 && vertical_acc < 0.5);
}

SafetyEvent analyzeIMUData(IMUData &data) {
  InternalDetectionState& d = detectionState;
  uint32_t currentTime = millis();
  
  // Update window
  accelWindow[windowIndex] = data.resultant_acc;
  gyroWindow[windowIndex] = data.resultant_gyro;
  windowIndex = (windowIndex + 1) % WINDOW_SIZE;
  
  float jerk = calcJerk(d, data.resultant_acc, currentTime);
  
  // TIER 1: SEVERE IMPACT
  if (data.resultant_acc > SEVERE_IMPACT_THRESHOLD_G) {
    d.currentState = InternalSafetyState::INJURY_LIKELY;
    d.detectedEvent = SafetyEvent::HEAVY_IMPACT;
    updateJerkHistory(d, data.resultant_acc, currentTime);
    return SafetyEvent::HEAVY_IMPACT;
  }
  
  // TIER 2: STATE MACHINE
  switch (d.currentState) {
    case InternalSafetyState::NORMAL: {
      // Freefall detected
      if (data.resultant_acc < FREEFALL_THRESHOLD_G) {
        d.freefallStartTime = currentTime;
        d.detectedEvent = SafetyEvent::FALL;
        d.currentState = InternalSafetyState::FREEFALL;
        d.preEventOrientation[0] = data.accX;
        d.preEventOrientation[1] = data.accY;
        d.preEventOrientation[2] = data.accZ;
      }
      // Direct impact with high jerk
      else if (data.resultant_acc > MEDIUM_IMPACT_THRESHOLD_G && 
               jerk > JERK_THRESHOLD_G_PER_S) {
        int impactCount = 0;
        for (int i = 0; i < WINDOW_SIZE; i++) {
          if (accelWindow[i] > MEDIUM_IMPACT_THRESHOLD_G) impactCount++;
        }
        if (impactCount >= SUSTAINED_THRESHOLD) {
          d.impactStartTime = currentTime;
          d.detectedEvent = SafetyEvent::DIRECT_IMPACT;
          d.currentState = InternalSafetyState::IMPACT;
        }
      }
      // High rotation + moderate acceleration
      else if (data.resultant_gyro > ROTATION_THRESHOLD_DEG_S && 
               data.resultant_acc > MEDIUM_IMPACT_THRESHOLD_G) {
        d.impactStartTime = currentTime;
        d.detectedEvent = SafetyEvent::DIRECT_IMPACT;
        d.currentState = InternalSafetyState::IMPACT;
      }
      break;
    }
    
    case InternalSafetyState::FREEFALL: {
      uint32_t freefallDuration = currentTime - d.freefallStartTime;
      
      if (data.resultant_acc > MEDIUM_IMPACT_THRESHOLD_G && 
          jerk > JERK_THRESHOLD_G_PER_S) {
        if (freefallDuration >= MIN_FREEFALL_DURATION_MS && 
            freefallDuration <= MAX_FREEFALL_TO_IMPACT_MS) {
          d.impactStartTime = currentTime;
          d.currentState = InternalSafetyState::IMPACT;
        } else {
          d.currentState = InternalSafetyState::RECOVERED;
        }
      }
      else if (freefallDuration > MAX_FREEFALL_TO_IMPACT_MS) {
        d.currentState = InternalSafetyState::RECOVERED;
      }
      break;
    }
    
    case InternalSafetyState::IMPACT: {
      uint32_t timeSinceImpact = currentTime - d.impactStartTime;
      if (timeSinceImpact > POST_IMPACT_OBS_DURATION_MS) {
        d.currentState = InternalSafetyState::POST_IMPACT;
        d.motionlessStartTime = currentTime;
      }
      break;
    }
    
    case InternalSafetyState::POST_IMPACT: {
      bool isHorizontal = checkPostImpactOrientation(data.accX, data.accY, data.accZ);
      bool isMotionless = (abs(data.resultant_acc - 1.0) < MOTIONLESS_ACC_THRESHOLD && 
                           data.resultant_gyro < MOTIONLESS_GYRO_THRESHOLD_DEG_S);
      
      if (isHorizontal && isMotionless) {
        uint32_t stationaryDuration = currentTime - d.motionlessStartTime;
        if (stationaryDuration > MOTIONLESS_THRESHOLD_MS) {
          d.currentState = InternalSafetyState::INJURY_LIKELY;
          updateJerkHistory(d, data.resultant_acc, currentTime);
          return d.detectedEvent;
        }
      } else if (!isMotionless) {
        d.currentState = InternalSafetyState::RECOVERED;
      } else {
        d.motionlessStartTime = currentTime;
      }
      break;
    }
    
    case InternalSafetyState::INJURY_LIKELY: {
      updateJerkHistory(d, data.resultant_acc, currentTime);
      return d.detectedEvent;
    }
    
    case InternalSafetyState::RECOVERED: {
      d.currentState = InternalSafetyState::NORMAL;
      d.detectedEvent = SafetyEvent::NONE;
      break;
    }
  }
  
  updateJerkHistory(d, data.resultant_acc, currentTime);
  return SafetyEvent::NONE;
}

#endif

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

    #if COLLECTION_TYPE == 1
    // Initialize detection state
    detectionState.currentState = InternalSafetyState::NORMAL;
    detectionState.detectedEvent = SafetyEvent::NONE;
    detectionState.freefallStartTime = 0;
    detectionState.impactStartTime = 0;
    detectionState.motionlessStartTime = 0;
    detectionState.prevResultantAcc = 1.0;
    detectionState.prevAccTime = millis();
    detectionState.prev2ResultantAcc = 1.0;
    detectionState.prev2AccTime = millis();
    detectionState.prev3ResultantAcc = 1.0;
    detectionState.prev3AccTime = millis();
    
    // Initialize windows
    for (int i = 0; i < WINDOW_SIZE; i++) {
        accelWindow[i] = 1.0;
        gyroWindow[i] = 0.0;
    }
    #endif

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

        #if COLLECTION_TYPE == 0
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
        #endif

        #if COLLECTION_TYPE == 1
        // Prepare IMU data
        IMUData data;
        data.accX = accel.acceleration.x / 9.81;
        data.accY = accel.acceleration.y / 9.81;
        data.accZ = accel.acceleration.z / 9.81;
        data.gyroX = gyro.gyro.x * 57.3;
        data.gyroY = gyro.gyro.y * 57.3;
        data.gyroZ = gyro.gyro.z * 57.3;
        data.resultant_acc = getResultant(data.accX, data.accY, data.accZ);
        data.resultant_gyro = getResultant(data.gyroX, data.gyroY, data.gyroZ);
        
        // Run fall detection algorithm
        SafetyEvent event = analyzeIMUData(data);
        
        // Calculate additional metrics
        float jerk = calcJerk(detectionState, data.resultant_acc, now);
        bool is_freefall = (detectionState.currentState == InternalSafetyState::FREEFALL);
        bool is_horizontal = checkPostImpactOrientation(data.accX, data.accY, data.accZ);
        bool is_motionless = (abs(data.resultant_acc - 1.0) < MOTIONLESS_ACC_THRESHOLD && 
                            data.resultant_gyro < MOTIONLESS_GYRO_THRESHOLD_DEG_S);

        if (LOGGING_MODE == 1) {
            Serial.printf("{\"ts\":%lu,\"ax\":%.3f,\"ay\":%.3f,\"az\":%.3f,"
                            "\"gx\":%.1f,\"gy\":%.1f,\"gz\":%.1f,"
                            "\"r_acc\":%.3f,\"r_gyro\":%.1f,\"state\":%u,\"event\":%u,\"jerk\":%.1f,"
                            "\"freefall\":%d,\"horizontal\":%d,\"motionless\":%d}\n",
                            now, data.accX, data.accY, data.accZ,
                            data.gyroX, data.gyroY, data.gyroZ,
                            data.resultant_acc, data.resultant_gyro,
                            (uint8_t)detectionState.currentState, (uint8_t)detectionState.detectedEvent, jerk,
                            is_freefall, is_horizontal, is_motionless);
        }
        else if (LOGGING_MODE == 2) {
            char payload[512];
            snprintf(payload, sizeof(payload),
                    "{\"ts\":%lu,\"ax\":%.3f,\"ay\":%.3f,\"az\":%.3f,"
                    "\"gx\":%.1f,\"gy\":%.1f,\"gz\":%.1f,"
                    "\"r_acc\":%.3f,\"r_gyro\":%.1f,\"state\":%u,\"event\":%u,\"jerk\":%.1f,"
                    "\"freefall\":%d,\"horizontal\":%d,\"motionless\":%d}",
                    now, data.accX, data.accY, data.accZ,
                    data.gyroX, data.gyroY, data.gyroZ,
                    data.resultant_acc, data.resultant_gyro,
                    (uint8_t)detectionState.currentState, (uint8_t)detectionState.detectedEvent, jerk,
                    is_freefall ? 1 : 0, is_horizontal ? 1 : 0, is_motionless ? 1 : 0);
            
            mqttClient.publish(MQTT_TOPIC_IMU_TEST, payload);
        }

        
        #endif

    }
  

}
