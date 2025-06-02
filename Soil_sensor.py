# soil_sensor.py
import paho.mqtt.client as mqtt
import requests
from datetime import datetime
import time
import json
import random

class SoilMoistureSensor:
    def __init__(self, catalog_url, location):
        self.catalog_url = catalog_url
        self.location = location
        self.sensor_id = None
        self.topic = None
        self.moisture = 40.0
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect

    def register(self):
        payload = {"type": "soil_sensor", "location": self.location}
        response = requests.post(f"{self.catalog_url}/register_device", json=payload)
        data = response.json()
        self.sensor_id = data["id"]
        self.topic = data["topic"]
        print(f"Registered with ID {self.sensor_id}, topic: {self.topic}")

    def on_connect(self, client, userdata, flags, rc):
        print("Connected to MQTT broker.")

    def simulate_reading(self):
        self.moisture += random.uniform(-5, 5)
        self.moisture = max(0, min(100, self.moisture))
        return round(self.moisture, 2)

    def publish_reading(self):
        reading = {
            "sensor_id": self.sensor_id,
            "moisture": self.simulate_reading(),
            "timestamp": time.time()
        }
        self.mqtt_client.publish(self.topic, json.dumps(reading))
        print(f"Published: {reading}")

    def run(self, broker="localhost", port=1883, interval=10):
        self.register()
        self.mqtt_client.connect(broker, port)
        self.mqtt_client.loop_start()
        try:
            while True:
                self.publish_reading()
                time.sleep(interval)
        except KeyboardInterrupt:
            self.mqtt_client.loop_stop()

if __name__ == "__main__":
    sensor = SoilMoistureSensor("http://localhost:8000", "garden_bed_1")
    sensor.run()
