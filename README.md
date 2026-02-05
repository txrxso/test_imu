# TEST IMU
For collecting IMU values for a variety of scenarios as part of threshold verification.

## SET UP 
1. `touch python/test_configs/mqtt_broker.yaml`
2. Put the following credentials in the .yaml file. This is used by the Python script to connect to the appropriate topic on the broker for data collection and analysis.

```yaml
public_broker:
  host: broker.hivemq.com
  port: 1883

private_broker:
  host: fe26426fbe64463790fc2792777c8189.s1.eu.hivemq.cloud
  port: 8883
  username: <PUT CREDS HERE>
  password: <PUT CREDS HERE>

topics:
  imu: igen430/shh/imu_test
  alerts: igen430/shh/alerts/workerA

```

3. Create the credentials file for the ESP32: <br>`touch include/secrets.h` <br>
Include the following:

```c++
#ifndef SECRETS_H
#define SECRETS_H

// WPA-2 wifi credentials - change these values to match your CWL
#define WIFI_SSID  "eduroam" 
#define WIFI_EAP_ID "cwl@ubc.ca"
#define WIFI_USER "cwl@ubc.ca"
#define WIFI_PASSWORD "pswd"

// Home wifi credentials or hot spot
#define HOTSPOT_SSID "wifi_ssid" 
#define HOTSPOT_PSWD "wifi_pswd"

#endif 
```
4. Add the appropriate Root CA certificate. 

To connect to `fe26426fbe64463790fc2792777c8189.s1.eu.hivemq.cloud` on port `8883` (TLS only), we need to set the Root CA certificate. <br>
In bash, run `touch include/certs.h`. <br>
Include the following: 
```c++
#ifndef CERTS_H
#define CERTS_H

// HiveMQ Cloud Root CA Certificate
const char* root_ca = <PASTE CERTIFICATE HERE>;

// the certificate that should be pasted includes the line 'BEGIN CERTIFICATE' up to, and including the line 'END CERTIFICATE'

#endif 
```


5. Add the required MQTT configuration. <br> In bash, run `touch include/mqtt_config.h`. Add the following: 

```c++
#ifndef MQTT_CONFIG_H
#define MQTT_CONFIG_H

const char* MQTT_SERVER_HIVEMQ_PUBLIC = "broker.hivemq.com"; //"test.mosquitto.org";
 
const int MQTT_PORT_HIVEMQ_PUBLIC = 1883; 
const char* MQTT_TOPIC_ALERTS = "igen430/shh/alerts/workerA";
const char* MQTT_TOPIC_HEARTBEATS = "igen430/shh/heartbeats/workerA";
const char* MQTT_TOPIC_IMU_TEST = "igen430/shh/imu_test";

// TLS + HIVE MQ PRIVATE BROKER
const char* MQTT_SERVER_HIVEMQ_PRIVATE = "fe26426fbe64463790fc2792777c8189.s1.eu.hivemq.cloud";
const int MQTT_PORT_HIVEMQ_TLS = 8883; 
const char* MQTT_TLS_URL = "fe26426fbe64463790fc2792777c8189.s1.eu.hivemq.cloud:8883";
const char* MQTT_USER = ""; // put username here
const char* MQTT_PSWD = ""; // put pswd here

#endif 
```


## Sample scenarios we want to collect data for and plot: 

### i) Dropping device from a height 
### ii) Shaking device vigorously
### iii) Walking around at normal pace with it on head
### iv) Running with it on head
### v) Turning head quickly from side to side
