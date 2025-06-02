import cherrypy
import json
import uuid
import os

class DataCatalog:
    def __init__(self):
        self.db_file = "catalog.json"
        if os.path.exists(self.db_file):
            with open(self.db_file, "r") as f:
                self.config_data = json.load(f)
        else:
            self.config_data = {
                "project": {
                    "name": "Smart Garden IoT System",
                    "version": "1.0",
                    "owners": ["Alireza Soleiman", "Masoud Momeni", "Setareh Ghorbani", "Niloofar Harati"]
                },
                "topics": {},
                "thresholds": {
                    "dry_soil": 30.0,
                    "optimal_soil": 50.0,
                    "rain_threshold": 5.0
                },
                "devices": {}
            }

    def save_config(self):
        with open(self.db_file, "w") as f:
            json.dump(self.config_data, f, indent=2)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def config(self):
        topics = {}
        for device_id, device in self.config_data["devices"].items():
            topic = self.config_data["topics"].get(device_id)
            if device["type"] == "soil_sensor" and "soil_moisture" not in topics:
                topics["soil_moisture"] = topic
            elif device["type"] == "weather_sensor" and "weather" not in topics:
                topics["weather"] = topic
            elif device["type"] == "water_pump" and "pump_control" not in topics:
                topics["pump_control"] = topic

        return {
            "project": self.config_data["project"],
            "topics": topics,
            "thresholds": self.config_data["thresholds"],
            "devices": self.config_data["devices"]
        }

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def devices(self):
        return self.config_data["devices"]

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def thresholds(self):
        return self.config_data["thresholds"]

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def topics(self):
        return self.config_data["topics"]

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def register_device(self):
        input_data = cherrypy.request.json
        device_type = input_data.get("type")
        location = input_data.get("location", "unknown")

        if device_type not in ["soil_sensor", "weather_sensor", "water_pump"]:
            return {"error": "Invalid device type"}

        unique_id = f"{device_type}_{uuid.uuid4().hex[:6]}"
        topic = f"garden/{'sensor' if 'sensor' in device_type else 'control'}/{device_type}_{location}"

        self.config_data["devices"][unique_id] = {
            "id": unique_id,
            "type": device_type,
            "location": location
        }
        self.config_data["topics"][unique_id] = topic
        self.save_config()

        return {
            "id": unique_id,
            "topic": topic
        }

if __name__ == "__main__":
    cherrypy.config.update({
        'server.socket_host': '127.0.0.1',
        'server.socket_port': 8000,
    })
    cherrypy.quickstart(DataCatalog())
