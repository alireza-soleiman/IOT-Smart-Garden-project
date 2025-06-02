# 🌱 Smart Garden IoT Project

This project simulates a smart garden using microservices. It monitors soil moisture and weather data, controls a water pump, and supports user interaction through a Telegram bot.


## 🚀 How to Run the Project

Make sure an MQTT broker (like Mosquitto) is running on `localhost:1883`.

Then run the following microservices **in order**:

1. Data catalog --->  Data_catalog.py
2. Devices --->  Soil_sensor.py  -   Weather_sensor.py  -  Water_pump.py
3. Statestic web servise --- > statestic _webservice.py
4. Controller ---> Controller.py
5. Telegram Bot --->  telegram_bot.py


* All system data (devices id , topics , ... ) are stored in `catalog.json` .
** All sensor data and pump logs are stored in `database.json`.
