# controller.py
import paho.mqtt.client as mqtt
import requests
import json
import time
import os

class CentralController:
    def __init__(self, catalog_url):
        self.catalog_url = catalog_url
        self.config = {}
        self.soil_topic = None
        self.weather_topic = None
        self.pump_topic = None
        self.last_soil_data = None
        self.last_weather_data = None

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

    def fetch_config(self):
        max_retries = 10
        retry_delay = 2
        for attempt in range(max_retries):
            try:
                response = requests.get(f"{self.catalog_url}/config")
                response.raise_for_status()
                config = response.json()
                topics = config.get("topics", {})

                if all(k in topics for k in ("soil_moisture", "weather", "pump_control")):
                    self.soil_topic = topics["soil_moisture"]
                    self.weather_topic = topics["weather"]
                    self.pump_topic = topics["pump_control"]
                    self.config = config  # ✅ Store the full config including thresholds
                    print("Configuration loaded successfully")
                    return
                else:
                    print(f"Required topics missing in response (attempt {attempt + 1}/{max_retries})")
            except Exception as e:
                print(f"Error fetching config (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(retry_delay)

        raise Exception("Could not load config with all required topics after multiple retries")

    def on_connect(self, client, userdata, flags, rc):
        print("Connected to MQTT broker.")
        if self.soil_topic:
            client.subscribe(self.soil_topic)
        if self.weather_topic:
            client.subscribe(self.weather_topic)

    def on_message(self, client, userdata, msg):
        payload = json.loads(msg.payload.decode())
        if msg.topic == self.soil_topic:
            self.last_soil_data = payload
        elif msg.topic == self.weather_topic:
            self.last_weather_data = payload
        self.evaluate_irrigation()

    def evaluate_irrigation(self):
        if not self.last_soil_data or not self.last_weather_data:
            return
        thresholds = self.config.get("thresholds", {"dry_soil": 30, "rain_threshold": 2})
        soil_moisture = self.last_soil_data["moisture"]
        rainfall = self.last_weather_data["rainfall"]
        if soil_moisture < thresholds["dry_soil"] and rainfall < thresholds["rain_threshold"]:
            print("Irrigation needed")
            self.activate_pump(10)

    def activate_pump(self, duration):
        command = {
            "command": "activate",
            "duration": duration,
            "timestamp": time.time()
        }
        self.mqtt_client.publish(self.pump_topic, json.dumps(command))
        print(f"Sent command: {command}")

        # Log pump activation
        log_entry = {
            "duration": duration,
            "timestamp": command["timestamp"]
        }



    def run(self, broker="localhost", port=1883):
        self.fetch_config()
        self.mqtt_client.connect(broker, port)
        self.mqtt_client.loop_forever()

if __name__ == "__main__":
    controller = CentralController("http://localhost:8000")
    controller.run()
