import gc
import time
import ubinascii
import machine
import micropython
import network
import esp
from umqttsimple import MQTTClient

esp.osdebug(None)
gc.collect()

ssid = 'SSID here'
password = 'Password here'
mqtt_server = 'your mqtt broker ip'

client_id = ubinascii.hexlify(machine.unique_id())
topic_sub = b'cat_commands'
topic_pub = b'cat_messages'


station = network.WLAN(network.STA_IF)

station.active(True)
station.connect(ssid, password)

while not station.isconnected():
    pass

print('Connection successful')
print(station.ifconfig())
