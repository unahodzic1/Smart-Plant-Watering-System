from machine import Pin, ADC, Timer
import network
import time
from umqtt.robust import MQTTClient

# Water level 

water_level_sensor = ADC(Pin(28))

# Maximum value that the water level sensor can read

max_value = 65535

# Relay that controls the pump

water_pump = Pin(26, Pin.OUT)

# Bar graph

pin = [22, 21, 20, 19, 18, 17, 16, 15, 14, 13]
led = []
for i in range(10):
    led.append(Pin(pin[i], Pin.OUT))

# Connecting to the WiFi

nic = network.WLAN(network.STA_IF)
nic.active(True)
nic.connect('Amina', 'amina123')

while not nic.isconnected():
    print("Waiting for connection ...")
    time.sleep(1)

print("WLAN connection established")
ipaddr = nic.ifconfig()[0]

print("Network settings:")
print(nic.ifconfig())

# Sub procedure executed upon receiving MQTT messages

def sub(topic, msg):
    print('Topic:', topic)
    print('Message:', msg)
    if topic == b'pico/WaterPumpOn':
        if msg == b'1':
            water_pump.value(1)
            print("Water pump on.")
            time.sleep(2)
            water_pump.value(0)
        else:
            water_pump.value(0)
    if topic == b'pico/YourPlant':
        if msg == b'Water the plant':
            water_pump.value(1)
            print("Water pump on.")
            time.sleep(2)
            water_pump.value(0)
        else:
            water_pump.value(0)

# Establishing connection with MQTT broker

mqtt_conn = MQTTClient(client_id='Pico2', server='broker.hivemq.com', user='', password='', port=1883)
mqtt_conn.set_callback(sub)
mqtt_conn.connect()
mqtt_conn.subscribe(b"pico/WaterPumpOn")  
mqtt_conn.subscribe(b"pico/YourPlant")  

def water_level_bar_graph():
    value = water_level_sensor.read_u16()
    num_leds = int((value / max_value) * 10)
    for i in range(10):
        led[i].value(1 if i < num_leds else 0)

def low_water_level():
    water_level = water_level_sensor.read_u16()
    if water_level < 6500:
        mqtt_conn.publish(b'pico/WaterLevel', b'0')
        print("Low water level.")
    if water_level > 6500:
        mqtt_conn.publish(b'pico/WaterLevel', b'1')

while True:
    mqtt_conn.check_msg()
    water_level_bar_graph()
    low_water_level()
    value = water_level_sensor.read_u16()
    print(value)
    time.sleep(1)