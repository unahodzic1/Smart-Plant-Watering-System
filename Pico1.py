from machine import Pin, ADC, SPI
from ili934xnew import ILI9341, color565
from micropython import const
from umqtt.robust import MQTTClient
from dht import DHT11
import network
import time
import ujson
import os
import glcdfont
import tt14
import tt24
import tt32

# Sensors

soil_moisture_sensor = ADC(Pin(28))
dht11_sensor = DHT11(Pin(26))

# TFT display

SCR_WIDTH = const(320)
SCR_HEIGHT = const(240)
SCR_ROT = const(2)
CENTER_Y = int(SCR_WIDTH / 2)
CENTER_X = int(SCR_HEIGHT / 2)

TFT_CLK_PIN = const(18)
TFT_MOSI_PIN = const(19)
TFT_MISO_PIN = const(16)
TFT_CS_PIN = const(17)
TFT_RST_PIN = const(20)
TFT_DC_PIN = const(15)

fonts = [glcdfont, tt14, tt24, tt32]

spi = SPI(
    0,
    baudrate=62500000,
    miso=Pin(TFT_MISO_PIN),
    mosi=Pin(TFT_MOSI_PIN),
    sck=Pin(TFT_CLK_PIN))

display = ILI9341(
    spi,
    cs=Pin(TFT_CS_PIN),
    dc=Pin(TFT_DC_PIN),
    rst=Pin(TFT_RST_PIN),
    w=SCR_WIDTH,
    h=SCR_HEIGHT,
    r=SCR_ROT)

# Displaying warning messages 

def print_high_temp_warning_message_TFT():
    display.set_pos(50, 50)
    display.rotation = 2
    display.set_font(tt14)
    display.set_color(color565(255, 255, 255), color565(0, 0, 0))
    display.print("High temperature! Move your plant!")

def print_low_water_lvl_warning_message_TFT():
    display.set_pos(50, 90)
    display.rotation = 2
    display.set_font(tt14)
    display.set_color(color565(255, 255, 255), color565(0, 0, 0))
    display.print("Low water level! Can't water the plant.")

# Connecting to the WiFi

nic = network.WLAN(network.STA_IF)
nic.active(True)
nic.connect('Lab220', 'lab220lozinka')

while not nic.isconnected():
    print("Waiting for connection...")
    time.sleep(1)

print("WLAN connection established.")
ipaddr = nic.ifconfig()[0]

print("Network settings:")
print(nic.ifconfig())

display_message_until = 0

# Sub procedure executed upon receiving MQTT messages

def sub(topic, msg):
    global display_message_until
    if topic == b'pico/WaterLevel':
        if msg == b'0':
            print_low_water_lvl_warning_message_TFT()
            display_message_until = time.time() + 3
        elif msg == b'1':
            display.erase()
            temperature_humidity()

# Establishing connection with MQTT broker

mqtt_conn = MQTTClient(client_id='Pico1', server='broker.hivemq.com', user='', password='', port=1883)
mqtt_conn.set_callback(sub)
mqtt_conn.connect()
mqtt_conn.subscribe(b"pico/WaterLevel") 

def low_soil_moisture():
    try:
        soil_moisture = soil_moisture_sensor.read_u16()
        if soil_moisture > 32000 and soil_moisture < 65000:
            mqtt_conn.publish(b'pico/WaterPumpOn', b'1')
            print("Message sent: Water pump is on.")
    except OSError as e:
        print("Error: ", e)

def print_soil_moisture():
    try:
        soil_moisture = soil_moisture_sensor.read_u16()
        max_moisture = 65535
        min_moisture = 1000
        moisture = (max_moisture - soil_moisture_sensor.read_u16()) * 100 / (max_moisture - min_moisture)
        msg = b'{\n "Soil moisture":' + str(round(moisture)).encode() + b'%\n}'
        mqtt_conn.publish(b'pico/YourPlant', msg)
    except OSError as e:
        print("Error: ", e)

def temperature_humidity():
    try:
        dht11_sensor.measure()
        temperature = dht11_sensor.temperature()
        humidity = dht11_sensor.humidity()
        if temperature > 10:
            print_high_temp_warning_message_TFT()
        else:
            display.erase()

    except OSError as e:
        print("Error:", e)

temp_humidity_interval = 60
soil_moisture_interval = 20
mqtt_check_interval = 1

last_temp_humidity_check = 0
last_soil_moisture_check = 0
last_mqtt_check = 0

while True:
    current_time = time.time()
    
    if current_time - last_mqtt_check >= mqtt_check_interval:
        mqtt_conn.check_msg()
        last_mqtt_check = current_time

    if current_time - last_temp_humidity_check >= temp_humidity_interval:
        temperature_humidity()
        last_temp_humidity_check = current_time

    if current_time - last_soil_moisture_check >= soil_moisture_interval:
        low_soil_moisture()
        print_soil_moisture()
        last_soil_moisture_check = current_time
    
    if display_message_until and current_time >= display_message_until:
        display.erase()
        display_message_until = 0
    
    time.sleep(0.1)



