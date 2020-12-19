# Copyright 2019 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import machine
device_id = ("DEV" + '{:02x}{:02x}{:02x}{:02x}'.format(machine.unique_id()[0], machine.unique_id()[1], machine.unique_id()[2], machine.unique_id()[3]))

""" ## start display
pin16 = machine.Pin(16, machine.Pin.OUT)
pin16.value(1)
import machine, ssd1306
i2c = machine.I2C(scl=machine.Pin(15), sda=machine.Pin(4))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
oled.fill(0)
oled.text('MicroPython', 0, 0)
oled.text('ESP32: ' + device_id, 0, 10)
oled.text('GCP IoT', 0, 20)    
oled.show()
"""

#BME680 config
from bme680 import *
from machine import I2C, Pin
bme = BME680_I2C(I2C(-1, Pin(21), Pin(22))) # Make sure to set the correct pins on for your device, not all pins work on all devices.

#Contiue Google Config

import esp32
from third_party import string
import network
import socket
import os
import utime
import ssl
from third_party import rsa
from umqtt.simple import MQTTClient
from ubinascii import b2a_base64
from machine import RTC, Pin
import ntptime
import ujson
import config

"""# Temperature and Humidity if you use a DHT Sensor you can use this code
import dht
from machine import Pin
sensor = dht.DHT22(Pin(12))"""

# Read the HCSR04 distance sensor sensor, this needs some updating though it isn't very accurate in its current workings. And, again ake sure to set the correct pins on for your device, not all pins work on all devices.
from HC_SR04 import HCSR04  
sr4sensor = HCSR04(trigger_pin=14, echo_pin=27,echo_timeout_us=10000) 

sta_if = network.WLAN(network.STA_IF)
led_pin = machine.Pin(config.device_config['led_pin'], Pin.OUT) #built-in LED pin
led_pin.value(1)

def on_message(topic, message):
    print((topic,message))

def connect():
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(config.wifi_config['ssid'], config.wifi_config['password'])
        while not sta_if.isconnected():
            pass
    print('network config: {}'.format(sta_if.ifconfig()))

def set_time():
    ntptime.settime()
    tm = utime.localtime()
    tm = tm[0:3] + (0,) + tm[3:6] + (0,)
    machine.RTC().datetime(tm)
    print('current time: {}'.format(utime.localtime()))

def b42_urlsafe_encode(payload):
    return string.translate(b2a_base64(payload)[:-1].decode('utf-8'),{ ord('+'):'-', ord('/'):'_' })

def create_jwt(project_id, private_key, algorithm, token_ttl):
    print("Creating JWT...")
    private_key = rsa.PrivateKey(*private_key)

    # Epoch_offset is needed because micropython epoch is 2000-1-1 and unix is 1970-1-1. Adding 946684800 (30 years)
    epoch_offset = 946684800
    claims = {
            # The time that the token was issued at
            'iat': utime.time() + epoch_offset,
            # The time the token expires.
            'exp': utime.time() + epoch_offset + token_ttl,
            # The audience field should always be set to the GCP project id.
            'aud': project_id
    }

    #This only supports RS256 at this time.
    header = { "alg": algorithm, "typ": "JWT" }
    content = b42_urlsafe_encode(ujson.dumps(header).encode('utf-8'))
    content = content + '.' + b42_urlsafe_encode(ujson.dumps(claims).encode('utf-8'))
    signature = b42_urlsafe_encode(rsa.sign(content,private_key,'SHA-256'))
    return content+ '.' + signature #signed JWT

def get_mqtt_client(project_id, cloud_region, registry_id, device_id, jwt):
    """Create our MQTT client. The client_id is a unique string that identifies
    this device. For Google Cloud IoT Core, it must be in the format below."""
    client_id = 'projects/{}/locations/{}/registries/{}/devices/{}'.format(project_id, cloud_region, registry_id, device_id)
    print('Sending message with password {}'.format(jwt))
    client = MQTTClient(client_id.encode('utf-8'),server=config.google_cloud_config['mqtt_bridge_hostname'],port=config.google_cloud_config['mqtt_bridge_port'],user=b'ignored',password=jwt.encode('utf-8'),ssl=True)
    client.set_callback(on_message)
    client.connect()
    client.subscribe('/devices/{}/config'.format(device_id), 1)
    client.subscribe('/devices/{}/commands/#'.format(device_id), 1)
    return client

connect()
#Need to be connected to the internet before setting the local RTC.
set_time()

jwt = create_jwt(config.google_cloud_config['project_id'], config.jwt_config['private_key'], config.jwt_config['algorithm'], config.jwt_config['token_ttl'])
client = get_mqtt_client(config.google_cloud_config['project_id'], config.google_cloud_config['cloud_region'], config.google_cloud_config['registry_id'], device_id, jwt)

while True:
    
    #Get New Sesor Readings You can use this for a DHT sensor instead of a BME680
    """sensor.measure() 
    temperature = sensor.temperature()
    humidity = sensor.humidity()"""
    
    #BME680 Readings
    temperature = str(round(bme.temperature, 2))
        #temp = (bme.temperature) * (9/5) + 32
        #temp = str(round(temp, 2)) + 'F'
    humidity = str(round(bme.humidity, 2))
    presure = str(round(bme.pressure, 2))
    mox = str(round(bme.gas/1000, 2))
    # Print some stuff if you want to see it in your output here or you can update the display here too.
    #print('Temperature:', temperature)
    #print('Humidity:', humidity)
    #print('Pressure:', presure)
    #print('Gas:', mox)
    #print('-------')
    #temperature = 18.7
    #humidity = 24.3
    # This reads the MQ 135 outoutm this really needs to be updated with some better code that fixes the readings for temp and humidity but it is a good starting point. Again make sure to set the right pin for your dev board.
    adc = machine.ADC(machine.Pin(36))
    mqsensor = adc.read()
    airquality = str(round(mqsensor/1024*100.0,2))
    distance = math.floor(abs(sr4sensor.distance_cm()))
    
    t = utime.localtime()
    timestamp = '{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}.000Z'.format(t[0], t[1], t[2], t[3], t[4], t[5])
    print(timestamp)
    message = {
            "device_id": device_id,
            "timestamp": timestamp,
            "devicetemp": esp32.raw_temperature(),
            "distance": distance,
            "temperature": temperature,
            "airquality": airquality,
            "humidity": humidity,
            "presure": presure,
            "mox": mox
        }
    print("Publishing message "+str(ujson.dumps(message)))
    led_pin.value(1)
    mqtt_topic = '/devices/{}/{}'.format(device_id, 'events')
    client.publish(mqtt_topic.encode('utf-8'), ujson.dumps(message).encode('utf-8'))
    led_pin.value(0)
    client.check_msg() # Check for new messages on subscription
    utime.sleep(30)  # Delay for 10 seconds.
