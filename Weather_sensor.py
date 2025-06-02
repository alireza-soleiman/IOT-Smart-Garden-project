# weather_sensor.py
import paho.mqtt.client as mqtt
import requests
from datetime import datetime
import time
import json
import random

class WeatherSensor:
    def __init__(self, catalog_url, location):
        self.catalog_url = catalog_url
        self.location = location
        self.sensor_id = None
        self.topic = None
        self.temperature = 20.0
        self.humidity = 50.0
        self.rainfall = 0.0
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect

    def register(self):
        payload = {"type": "weather_sensor", "location": self.location}
        response = requests.post(f"{self.catalog_url}/register_device", json=payload)
        data = response.json()
        self.sensor_id = data["id"]
        self.topic = data["topic"]
        print(f"Registered with ID {self.sensor_id}, topic: {self.topic}")

    def on_connect(self, client, userdata, flags, rc):
        print("Connected to MQTT broker.")

    def simulate_reading(self):
        self.temperature += random.uniform(-1, 1)
        self.humidity = min(100, max(0, self.humidity + random.uniform(-5, 5)))
        self.rainfall += random.uniform(0, 2) if random.random() < 0.1 else -0.1
        self.rainfall = max(0, self.rainfall)
        return {
            "temperature": round(self.temperature, 2),
            "humidity": round(self.humidity, 2),
            "rainfall": round(self.rainfall, 2)
        }

    def publish_reading(self):
        reading = {
            "sensor_id": self.sensor_id,
            **self.simulate_reading(),
            "timestamp": time.time()
        }
        self.mqtt_client.publish(self.topic, json.dumps(reading))
        print(f"Published: {reading}")

    def run(self, broker="localhost", port=1883, interval=15):
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
    sensor = WeatherSensor("http://localhost:8000", "roof")
    sensor.run()
