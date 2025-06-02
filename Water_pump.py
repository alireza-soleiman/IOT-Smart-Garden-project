import paho.mqtt.client as mqtt
import requests
import json
import time

class WaterPump:
    def __init__(self, catalog_url, location):
        self.catalog_url = catalog_url
        self.location = location
        self.device_id = None
        self.topic = None
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

    def register(self):
        payload = {"type": "water_pump", "location": self.location}
        response = requests.post(f"{self.catalog_url}/register_device", json=payload)
        data = response.json()
        self.device_id = data["id"]
        self.topic = data["topic"]
        print(f"Registered with ID {self.device_id}, topic: {self.topic}")

    def on_connect(self, client, userdata, flags, rc):
        print("Connected to MQTT broker.")
        self.mqtt_client.subscribe(self.topic)

    def on_message(self, client, userdata, msg):
        command = json.loads(msg.payload.decode())
        if command.get("command") == "activate":
            duration = command.get("duration", 5)
            print(f"Activating pump for {duration} seconds...")
            time.sleep(duration)
            print("Pump deactivated.")

    def run(self, broker="localhost", port=1883):
        self.register()
        self.mqtt_client.connect(broker, port)
        self.mqtt_client.loop_forever()

if __name__ == "__main__":
    pump = WaterPump("http://localhost:8000", "shed")
    pump.run()
