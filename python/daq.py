# Data Acquisition Script for Collecting IMU Data

# Some scenarios to consider:
# Dropping device from a height 
# Shaking device vigorously
# Walking around at normal pace with it on head
# Running with it on head
# Turning head quickly from side to side

import csv, json, os, re, sys, signal
from datetime import datetime
import pandas as pd 
import matplotlib.pyplot as plt

def get_logging_mode(): 
    """Extract LOGGING_MODE from .cpp file"""
    cpp_path = os.path.join(os.path.dirname(__file__), "..", "src", "imu_collection.cpp")

    with open(cpp_path, "r") as f:
        content = f.read()
    
    match = re.search(r'#define\s+LOGGING_MODE\s+(\d+)', content)
    if match:
        return int(match.group(1))
    
    print("Could not find LOGGING_MODE in imu_collection.cpp")
    return None

def get_mqtt_config():
    """Extract MQTT configuration from mqtt_config.h"""
    config_path = os.path.join(os.path.dirname(__file__), "..", "include", "mqtt_config.h")
    
    with open(config_path, "r") as f:
        content = f.read()
    
    config = {}
    
    # Extract string values
    host_match = re.search(r'MQTT_SERVER_HIVEMQ_PRIVATE\s*=\s*"([^"]+)"', content)
    if host_match:
        config['host'] = host_match.group(1)
    
    topic_match = re.search(r'MQTT_TOPIC_IMU_TEST\s*=\s*"([^"]+)"', content)
    if topic_match:
        config['topic'] = topic_match.group(1)
    
    user_match = re.search(r'MQTT_USER\s*=\s*"([^"]*)"', content)
    if user_match:
        config['username'] = user_match.group(1)
    
    pswd_match = re.search(r'MQTT_PSWD\s*=\s*"([^"]*)"', content)
    if pswd_match:
        config['password'] = pswd_match.group(1)
    
    # Extract port value
    port_match = re.search(r'MQTT_PORT_HIVEMQ_TLS\s*=\s*(\d+)', content)
    if port_match:
        config['port'] = int(port_match.group(1))
    
    return config

def log_value():
    mode = get_logging_mode()
    
    if mode == 1:
        print("Detected LOGGING_MODE=1 (Serial)")
        port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
        return serial_mode(port)
    elif mode == 2:
        print("Detected LOGGING_MODE=2 (MQTT)")
        return mqtt_mode()
    else:
        print(f"LOGGING_MODE={mode} not supported (use 1 or 2)")
        return 1

def auto_gen_plots(csv_file):
    """Generate plots from logged CSV data."""
    df = pd.read_csv(csv_file)
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    
    # Accelerometer plot
    axes[0].plot(df['ts'], df['ax'], label='ax', alpha=0.7)
    axes[0].plot(df['ts'], df['ay'], label='ay', alpha=0.7)
    axes[0].plot(df['ts'], df['az'], label='az', alpha=0.7)
    axes[0].set_xlabel('Time (ms)')
    axes[0].set_ylabel('Acceleration (m/s²)')
    axes[0].set_title('Accelerometer Data')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Gyroscope plot
    axes[1].plot(df['ts'], df['gx'], label='gx', alpha=0.7)
    axes[1].plot(df['ts'], df['gy'], label='gy', alpha=0.7)
    axes[1].plot(df['ts'], df['gz'], label='gz', alpha=0.7)
    axes[1].set_xlabel('Time (ms)')
    axes[1].set_ylabel('Angular Velocity (rad/s)')
    axes[1].set_title('Gyroscope Data')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plot_file = csv_file.replace('.csv', '.png')
    plt.savefig(plot_file, dpi=300)
    print(f"Plot saved to {plot_file}")
    plt.show()

def serial_mode(port, baud=115200): 
    try:
        import serial
    except ImportError:
        print("pyserial not installed. Run: pip install pyserial")
        return 1
    
    # Ensure test_data directory exists
    test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")
    os.makedirs(test_data_dir, exist_ok=True)
    
    out_file = os.path.join(test_data_dir, f"imu_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ts", "ax", "ay", "az", "gx", "gy", "gz"])
        writer.writeheader()
        
        def handle_exit(_signum, _frame):
            print(f"\nSaved {out_file}")
            f.close()
            auto_gen_plots(out_file)
            sys.exit(0)
        
        signal.signal(signal.SIGINT, handle_exit)
        
        print(f"Opening serial port {port} at {baud} baud...")
        ser = serial.Serial(port, baud, timeout=1)
        print(f"Logging to {out_file}")
        print("Press Ctrl+C to stop\n")
        
        while True:
            try:
                line = ser.readline().decode("utf-8").strip()
                if not line or not line.startswith("{"):
                    continue
                
                data = json.loads(line)
                writer.writerow({
                    "ts": data.get("ts"),
                    "ax": data.get("ax"),
                    "ay": data.get("ay"),
                    "az": data.get("az"),
                    "gx": data.get("gx"),
                    "gy": data.get("gy"),
                    "gz": data.get("gz"),
                })
                f.flush()
                print(line)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                print(f"Bad data: {exc}")
            except KeyboardInterrupt:
                break
        
        ser.close()
    
    auto_gen_plots(out_file)
    return 0


def mqtt_mode():
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        print("paho-mqtt not installed. Run: pip install paho-mqtt")
        return 1
    
    config = get_mqtt_config()
    host = config.get('host', 'fe26426fbe64463790fc2792777c8189.s1.eu.hivemq.cloud')
    port = config.get('port', 8883)
    topic = config.get('topic', 'igen430/shh/imu_test')
    username = config.get('username', '')
    password = config.get('password', '')
    
    # Ensure test_data directory exists
    test_data_dir = os.path.join(os.path.dirname(__file__), "test_data", "raw")
    os.makedirs(test_data_dir, exist_ok=True)
    
    out_file = os.path.join(test_data_dir, f"imu_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ts", "ax", "ay", "az", "gx", "gy", "gz"])
        writer.writeheader()
        
        def handle_exit(_signum, _frame):
            print(f"\nSaved {out_file}")
            f.close()
            auto_gen_plots(out_file)
            sys.exit(0)
        
        signal.signal(signal.SIGINT, handle_exit)
        
        client = mqtt.Client()
        
        if username and password:
            client.username_pw_set(username, password)
            client.tls_set()
        
        def on_connect(_client, _userdata, _flags, rc):
            if rc == 0:
                print(f"Connected to MQTT broker {host}:{port}")
                _client.subscribe(topic)
                print(f"Subscribed to {topic}")
                print(f"Logging to {out_file}")
                print("Press Ctrl+C to stop\n")
            else:
                print(f"Connection failed with code {rc}")
        
        def on_message(_client, _userdata, msg):
            try:
                payload = msg.payload.decode("utf-8")
                data = json.loads(payload)
                writer.writerow({
                    "ts": data.get("ts"),
                    "ax": data.get("ax"),
                    "ay": data.get("ay"),
                    "az": data.get("az"),
                    "gx": data.get("gx"),
                    "gy": data.get("gy"),
                    "gz": data.get("gz"),
                })
                f.flush()
                print(payload)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                print(f"Bad payload: {exc}")
        
        client.on_connect = on_connect
        client.on_message = on_message
        
        print(f"Connecting to {host}:{port}...")
        client.connect(host, port, keepalive=60)
        client.loop_forever()
    
    auto_gen_plots(out_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(log_value()) 
