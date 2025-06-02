import paho.mqtt.client as mqtt
import cherrypy
import json
import time
import os
import requests
import datetime


class StatsServer:
    def __init__(self, catalog_url, broker="localhost", port=1883):
        self.catalog_url = catalog_url
        self.broker = broker
        self.port = port

        self.topics = {}

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

    def fetch_config(self):
        print("Fetching configuration from catalog...")
        try:
            response = requests.get(f"{self.catalog_url}/config")
            response.raise_for_status()
            config = response.json()
            topics = config.get("topics", {})
            if not topics:
                raise Exception("No topics found in catalog config")
            self.topics = topics
            print(f"Topics loaded from catalog: {self.topics}")
        except Exception as e:
            print(f"Failed to fetch config: {e}")
            raise

    def on_connect(self, client, userdata, flags, rc):
        print("Connected to MQTT broker.")
        for topic_name, topic_str in self.topics.items():
            client.subscribe(topic_str)
            print(f"Subscribed to topic '{topic_name}': {topic_str}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
        except json.JSONDecodeError:
            print(f"Invalid JSON on topic {msg.topic}, skipping.")
            return

        print(f"📥 Received message on topic {msg.topic}: {payload}")

        topic_type = None
        for key, topic in self.topics.items():
            if msg.topic == topic:
                topic_type = key
                break

        if topic_type is None:
            print(f"Unknown topic {msg.topic}, skipping")
            return

        if topic_type == "soil_moisture":
            self.save_to_db("soil_moisture", payload)
        elif topic_type == "weather":
            self.save_to_db("weather", payload)
        elif topic_type == "pump_control":
            self.save_pump_activation(payload)
        else:
            print(f"Unhandled topic type {topic_type}")
                   

    def save_to_db(self, sensor_type, payload):
        timestamp = payload.get("timestamp", time.time())
        date_key = time.strftime("%Y-%m-%d", time.localtime(timestamp))

        db = self.load_db()

        if date_key not in db:
            db[date_key] = {}
        if sensor_type not in db[date_key]:
            db[date_key][sensor_type] = []

        db[date_key][sensor_type].append(payload)

        self.save_db(db)
        print(f"✅ Saved {sensor_type} data for {date_key}")

    def save_pump_activation(self, payload):
        timestamp = payload.get("timestamp", time.time())
        duration = payload.get("duration")
        if duration is None:
            print("Pump activation payload missing 'duration', skipping.")
            return

        date_key = time.strftime("%Y-%m-%d", time.localtime(timestamp))
        log_entry = {"timestamp": timestamp, "duration": duration}

        db = self.load_db()

        if date_key not in db:
            db[date_key] = {}
        if "pump_activations" not in db[date_key]:
            db[date_key]["pump_activations"] = []

        db[date_key]["pump_activations"].append(log_entry)

        self.save_db(db)
        print(f"✅ Saved pump activation: {log_entry}")

    def load_db(self):
        if os.path.exists("database.json"):
            try:
                with open("database.json", "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("⚠️ Corrupted database.json, starting fresh.")
                return {}
        return {}

    def save_db(self, db):
        with open("database.json", "w") as f:
            json.dump(db, f, indent=2)


    @cherrypy.expose
    @cherrypy.tools.json_out()
    def soil(self):

        try:
            with open("database.json", "r") as f:
                db = json.load(f)

            all_dates = sorted(db.keys(), reverse=True)
            for date in all_dates:
                soil_data = db[date].get("soil_moisture")
                if soil_data:
                    latest = format_timestamp(soil_data[-1])
                    avg = sum(d["moisture"] for d in soil_data) / len(soil_data)
                    return {
                        "latest": latest,
                        "average_moisture": round(avg,2),
                        "readings_count": len(soil_data)
                    }

            return {"error": "No data available"}
        except Exception as e:
            return {"error": str(e)}
            

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def weather(self):
        try:
            with open("database.json", "r") as f:
                db = json.load(f)

            all_dates = sorted(db.keys(), reverse=True)
            for date in all_dates:
                weather_data = db[date].get("weather")
                if weather_data:
                    latest = format_timestamp(weather_data[-1])
                    avg_temp = sum(d["temperature"] for d in weather_data) / len(weather_data)
                    avg_humidity = sum(d["humidity"] for d in weather_data) / len(weather_data)
                    total_rain = sum(d["rainfall"] for d in weather_data)
                    return {
                        "latest": latest,
                        "average_temperature": round(avg_temp,2),
                        "average_humidity": round(avg_humidity,2),
                        "total_rainfall": total_rain,
                        "readings_count": len(weather_data)
                    }

            return {"error": "No data available"}
        except Exception as e:
            return {"error": str(e)}
        
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def pump(self):
        try:
            with open("database.json", "r") as f:
                db = json.load(f)

            all_dates = sorted(db.keys(), reverse=True)
            all_activations = []
            for date in all_dates:
                activations = db[date].get("pump_activations", [])
                all_activations.extend(activations)

            if not all_activations:
                return {
                    "total_activations": 0,
                    "last_activation": None,
                    "activations": []
                }

            last = format_timestamp(all_activations[-1])
            formatted_activations = [format_timestamp(a) for a in all_activations]

            return {
                "total_activations": len(all_activations),
                "last_activation": last,
                "activations": formatted_activations
            }
        except Exception as e:
            return {"error": str(e)}


    def run(self):
        self.fetch_config()
        self.mqtt_client.connect(self.broker, self.port)
        self.mqtt_client.loop_start()

        cherrypy.config.update({
            'server.socket_host': '127.0.0.1',
            'server.socket_port': 5001,
            'log.screen': True
        })

        cherrypy.quickstart(self)

def format_timestamp(entry):
        #Convert timestamp to readable format if present
            if isinstance(entry, dict) and "timestamp" in entry:
                entry = entry.copy()
                try:
                    entry["timestamp"] = datetime.datetime.fromtimestamp(entry["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    entry["timestamp"] = "Invalid timestamp"
            return entry

if __name__ == "__main__":
    server = StatsServer("http://localhost:8000")  
    server.run()
