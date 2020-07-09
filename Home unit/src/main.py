# Code By Mohmmad Qasem As a part of course project in Applied IOT course at Linné University
# 21 JUN 2020
# The button click, double click and hold logic is taken from "4-Way Button" Arduino sketch By Jeff Saltzman Oct. 13, 2009 and translated into micropython by me

import time
import Adafruit_SSD1306 as SSD1306  # for the oled screen
import NRF24L01
import ustruct as struct
from machine import Pin, SPI, I2C, PWM

# ================ HSPI=================================
cs_pin = Pin(21)
sck_pin = Pin(14)
mosi_pin = Pin(13)
miso_pin = Pin(12)
ce_pin = Pin(27)
hspi = SPI(1, sck=sck_pin, mosi=mosi_pin, miso=miso_pin)
# =======================================================

# ================= NRF24L01=============================
READING_PIPE = "Pipe1".encode()
WRITING_PIPE = "Pipe0".encode()

# initialize the NRF24 module
radio = NRF24L01.NRF24L01(hspi, cs=cs_pin, ce=ce_pin,
                          channel=85, payload_size=6)
radio.set_crc(2)  # set the CRC to 16 bytes
# set the datarate and power (datarate most match on both sides)
radio.set_power_speed(NRF24L01.POWER_3, NRF24L01.SPEED_250K)
# open the writing and reading pipes
radio.open_rx_pipe(1, READING_PIPE)
radio.open_tx_pipe(WRITING_PIPE)
radio_timeout_delay = 7  # seconds
radio_timeout_time = 0  # ms
radio_timedout = False

radio_commands = {"NONE": 0, "Disable": 1, "Start": 2, "Enable": 3}


def send_command(command_number):
    print("sending command:", command_number)
    if not (command_number < 1 or command_number > 4):
        command = struct.pack(struct_format, command_number)
        print(command)
        try:
            radio.stop_listening()
            radio.send(command)
            radio.start_listening()
            return True
        except OSError as error:
            print("error:", error)
            radio.start_listening()
            return False
# ==========================================================


# ================== I2C + OLED ============================
OLED_WIDTH = 128
OLED_HEIGHT = 64
# Width of font characters in pixels. (used to position text on the screen)
FONT_WIDTH = 8
# Height of the font characters in pixels. (used to position text on the screen)
FONT_HEIGHT = 8

# reset screen
oled_RST_pin = Pin(16, Pin.OUT)
oled_RST_pin.value(1)

i2c = I2C(-1, scl=Pin(15), sda=Pin(4))  # initalize i2c
# initalize the ssd1306 oled screen
oled = SSD1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)
# ================================================================


#  ===================Buzzer Declarations================
beeper = PWM(Pin(23, Pin.OUT), freq=440, duty=0)
alarm_sound_time = 0
time_since_last_tone = 0
alarm_running = False
# ===============================================================

# ================ Button Declarations =====================
HIGH = 1  # used instead of replacing the variable in the original code
LOW = 0  # used instead of replacing the variable in the original code
# Button timing variables
debounce = 20  # ms debounce period to prevent flickering when pressing or releasing the button
DC_gap = 250            # max ms between clicks for a double click event
hold_time = 1000        # ms hold period: how long to wait for press+hold event


class AdvancedButton:
    button = None
    button_val = HIGH   # value read from button
    button_last = HIGH  # buffered value of the button's previous state
    DC_waiting = False  # whether we're waiting for a double click (down)
    # whether to register a double click on next release, or whether to wait and click
    DC_on_up = False
    single_OK = True    # whether it's OK to do a single click
    down_time = 0         # time the button was pressed down
    up_time = 0          # time the button was released
    # whether to ignore the button release because the click+hold was triggered
    ignore_up = False
    wait_for_up = False        # when held, whether to wait for the up event
    hold_event_past = False    # whether or not the hold event happened already
    long_hold_event_past = False  # whether or not the long hold event happened already

    def __init__(self, pin):
        self.button = Pin(pin, Pin.IN, Pin.PULL_UP)
        self.button.value(HIGH)


green_button = AdvancedButton(5)
red_button = AdvancedButton(18)
# ================================================================

# ================= Button Functions ================


def red_click_event():
    print("red click")
    global alarm_state, alarm_running
    if(alarm_running):
        alarm_running = False
    if(alarm_state):
        oled.fill(0)
        oled.invert(0)
        alarm_state = False
    if(not alarm_state and not alarm_running):
        if(send_command(radio_commands["Disable"])):
            oled.fill(0)


def red_double_click_event():
    print("red double click")
    # does nothing for now


def red_hold_event():
    print("red hold")
    if(client is None):
        connect_client()


def green_click_event():
    print("green click")
    global alarm_state, alarm_running
    if(alarm_running):
        alarm_running = False
    if(alarm_state):
        oled.fill(0)
        oled.invert(0)
        alarm_state = False
    if not alarm_state and not alarm_running:
        if(send_command(radio_commands["Start"])):
            oled.fill(0)


def green_double_click_event():
    print("green double click")
    # does nothing for now


def green_hold_event():
    print("green hold")
    print("green click")
    global alarm_state, alarm_running
    if(alarm_running):
        alarm_running = False
    if(alarm_state):
        oled.fill(0)
        oled.invert(0)
        alarm_state = False
    if not alarm_state and not alarm_running:
        if(send_command(radio_commands["Enable"])):
            oled.fill(0)


def checkButton(advanced_button):
    event = 0
    # Button pressed down
    advanced_button.button_val = advanced_button.button.value()
    if advanced_button.button_val == LOW and advanced_button.button_last == HIGH and (time.ticks_diff(time.ticks_ms(), advanced_button.up_time)) > debounce:
        advanced_button.down_time = time.ticks_ms()
        advanced_button.ignore_up = False
        advanced_button.wait_for_up = False
        advanced_button.single_OK = True
        advanced_button.hold_event_past = False
        if (time.ticks_diff(time.ticks_ms(), advanced_button.up_time) < DC_gap and advanced_button.DC_on_up == False and advanced_button.DC_waiting == True):
            advanced_button.DC_on_up = True
        else:
            advanced_button.DC_on_up = False
        advanced_button.DC_waiting = False
    # Button released
    elif (advanced_button.button_val == HIGH and advanced_button.button_last == LOW and (time.ticks_diff(time.ticks_ms(), advanced_button.down_time) > debounce)):
        if (not advanced_button.ignore_up):
            advanced_button.up_time = time.ticks_ms()
            if (advanced_button.DC_on_up == False):
                advanced_button.DC_waiting = True
            else:
                event = 2
                advanced_button.DC_on_up = False
                advanced_button.DC_waiting = False
                advanced_button.single_OK = False
    # Test for normal click event: DC_gap expired
    if (advanced_button.button_val == HIGH and (time.ticks_diff(time.ticks_ms(), advanced_button.up_time)) >= DC_gap and advanced_button.DC_waiting == True and advanced_button.DC_on_up == False and advanced_button.single_OK == True and event != 2):
        event = 1
        advanced_button.DC_waiting = False
    # Test for hold
    if (advanced_button.button_val == LOW and (time.ticks_diff(time.ticks_ms(), advanced_button.down_time)) >= hold_time):
        # Trigger "normal" hold
        if (not advanced_button.hold_event_past):
            event = 3
            advanced_button.wait_for_up = True
            advanced_button.ignore_up = True
            advanced_button.DC_on_up = False
            advanced_button.DC_waiting = False
            # advanced_button.down_time = time.ticks_ms()
            advanced_button.hold_event_past = True
    advanced_button.button_last = advanced_button.button_val
    return event
# ================================================================

# ===================== MQTT ======================================


def mqtt_msg_callback(topic, msg):
    if topic == b'cat_commands':
        try:
            command = int(msg)
            send_command(command)
            print("mqtt command excuted command: ", msg)
        except Exception:
            print("mqtt command couldn't be interpreted; command: ", msg)
    else:
        print("mqtt command recived but topic differs; topic:", topic)


def connect_and_subscribe():
    global client_id, mqtt_server, topic_sub  # defined in boot.py
    client = MQTTClient(client_id, mqtt_server)
    client.set_callback(mqtt_msg_callback)
    client.connect()
    client.subscribe(topic_sub)
    print('Connected to MQTT broker')
    return client


def connect_client():
    global oled
    global client
    oled.fill(0)
    connection_msg = "MQTT Connecting"
    print(connection_msg)
    oled.text(connection_msg, int(OLED_WIDTH/2 -
                                  len(connection_msg)*8/2), int(OLED_HEIGHT/2-8/2))
    oled.show()
    try:
        client = connect_and_subscribe()
    except OSError as e:
        client = None
        print("MQTT FAILED")
    oled.fill(0)
# =================================================================


# ======================= Drawing ===============================
temp = [[0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
        [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
        [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
        [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
        [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0]]
cat = [[0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0],
       [0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0],
       [0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0],
       [0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0],
       [0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0],
       [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
       [0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0],
       [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
       [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
       [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
       [0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0],
       [0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0],
       [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
       [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
       [0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0],
       [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0]]
warning = [[0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
           [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0],
           [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0],
           [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
           [0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0],
           [0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0],
           [0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0],
           [0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 0, 0],
           [0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0],
           [0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0],
           [0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0],
           [0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0],
           [0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0],
           [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
           [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
           [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]
state = [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0],
         [0, 0, 0, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 0],
         [0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0],
         [0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0],
         [0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0],
         [0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1],
         [0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1],
         [0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1],
         [0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1],
         [0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0],
         [0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0],
         [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
         [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
         [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]
mqtt_connected = [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
                  [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
                  [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
                  [0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0],
                  [0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0],
                  [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
                  [0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0],
                  [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]
mqtt_disconnected = [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0],
                     [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0],
                     [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
                     [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
                     [0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 1, 0],
                     [0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0],
                     [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
                     [0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0],
                     [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0],
                     [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
                     [0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
                     [0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0],
                     [0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0],
                     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]

bar_pos = 0  # variable to indicate the animated bar position
animation_time = 0

temp_draw_pos = {"x": 0, "y": 0}
state_draw_pos = {"x": 0, "y": 16}
warning_draw_pos = {"x": 127-16, "y": 16+8}
mqtt_draw_pos = {"x": 127-16, "y": 0}


temp_draw_pos["indicator"] = {
    "x": temp_draw_pos["x"]+7, "y": temp_draw_pos["y"]}
state_draw_pos["indicator"] = {
    "x": state_draw_pos["x"]+7, "y": state_draw_pos["y"]+1}
warning_draw_pos["indicator"] = {
    "x": warning_draw_pos["x"]+8, "y": warning_draw_pos["y"]}
mqtt_draw_pos["indicator"] = {
    "x": mqtt_draw_pos["x"]+5, "y": mqtt_draw_pos["y"]+1}


def draw_symbol(oled, shape, x=0, y=0):
    for i, row in enumerate(shape):
        for j, c in enumerate(row):
            oled.pixel(j+x, i+y, c)


def animate_bar(oled):
    global bar_pos
    oled.fill_rect(0, OLED_HEIGHT-4, OLED_WIDTH, 4, 0)  # empty the line
    # draw line at the new position
    oled.fill_rect(bar_pos, OLED_HEIGHT-4, 8, 4, 1)
    bar_pos += 8
    if(bar_pos > 128):
        bar_pos = 0


def draw_status_screen(oled):
    global animation_time
    oled.invert(0)
    if(time.ticks_diff(time.ticks_ms(), animation_time) > 500):
        animation_time = time.ticks_ms()
        # check the indicator pixel of the temp symbol to see if already drawn (0 is relative to the symbol itself)
        if(not oled.pixel(temp_draw_pos["indicator"]["x"], temp_draw_pos["indicator"]["y"])):
            draw_symbol(oled, temp, temp_draw_pos["x"], temp_draw_pos["y"])
        # check the x:7 y:1 pixel of the state symbol to see if already drawn (0 is relative to the symbol itself)
        if(not oled.pixel(state_draw_pos["indicator"]["x"], state_draw_pos["indicator"]["y"])):
            draw_symbol(oled, state, state_draw_pos["x"], state_draw_pos["y"])
        oled.fill_rect(16, 0, 95, 48, 0)  # ! erase the text only
        oled.text(str(latest_values[0])+" C", 16+8, 16-12)
        oled.text(str(latest_values[1]), 16+8, 32-12)

        if ((latest_values[0] != None) and (latest_values[0] <= 1)) or radio_timedout:
            # check the x:8 y:0 pixel of the warning symbol to see if already drawn (0 is relative to the symbol itself)
            if(not oled.pixel(warning_draw_pos["indicator"]["x"], warning_draw_pos["indicator"]["y"])):
                draw_symbol(oled, warning,
                            warning_draw_pos["x"], warning_draw_pos["y"])
        else:
            oled.fill_rect(127-16, 16+8, 16, 16, 0)
        if(client is not None):  # mqtt connected
            # check the x:5 y:0 pixel of the wifi symbol to see if already drawn (0 is relative to the symbol itself)
            if(oled.pixel(mqtt_draw_pos["indicator"]["x"], mqtt_draw_pos["indicator"]["y"]) and oled.pixel(mqtt_draw_pos["x"]+13, mqtt_draw_pos["y"])):
                oled.fill_rect(mqtt_draw_pos["x"],
                               mqtt_draw_pos["y"], 16, 16, 0)
                draw_symbol(oled, mqtt_connected,
                            mqtt_draw_pos["x"], mqtt_draw_pos["y"])
            elif(not oled.pixel(mqtt_draw_pos["indicator"]["x"], mqtt_draw_pos["indicator"]["y"])):
                draw_symbol(oled, mqtt_connected,
                            mqtt_draw_pos["x"], mqtt_draw_pos["y"])
        else:
            if oled.pixel(mqtt_draw_pos["indicator"]["x"], mqtt_draw_pos["indicator"]["y"]) and not oled.pixel(mqtt_draw_pos["x"]+13, mqtt_draw_pos["y"]):
                oled.fill_rect(mqtt_draw_pos["x"],
                               mqtt_draw_pos["y"], 16, 16, 0)
                draw_symbol(oled, mqtt_disconnected,
                            mqtt_draw_pos["x"], mqtt_draw_pos["y"])
            elif not oled.pixel(mqtt_draw_pos["indicator"]["x"], mqtt_draw_pos["indicator"]["y"]):
                draw_symbol(oled, mqtt_disconnected,
                            mqtt_draw_pos["x"], mqtt_draw_pos["y"])
        animate_bar(oled)


def draw_alarm_screen(oled, text, symbol):
    oled.fill(0)
    oled.invert(1)
    x = int(OLED_WIDTH / 2 - (len(text)*FONT_WIDTH) / 2)
    y = int(OLED_HEIGHT / 2 - (FONT_HEIGHT) / 2)
    oled.text(text, x, y)
    for i in range(8):
        draw_symbol(oled, symbol, i*16, 0)
        draw_symbol(oled, symbol, i*16, OLED_HEIGHT-16)
# ================================================================


# =================== Other Vars=========================
struct_format = '<bfb'
# boolean to indicate if the device is in alarm state (Cat- or high temp detected)
alarm_state = False
# stores the latest values to be shown on the oled screen
latest_values = [None, None]
# ======================================================


# ==================== Setup =====================
client = None
connect_client()
radio.start_listening()  # start listning for packets
# =================================================

# =================== Main loop ===================
while True:
    # check how the red button is pressed
    red_b = checkButton(red_button)
    if red_b == 1:
        red_click_event()
    if red_b == 2:
        red_double_click_event()
    if red_b == 3:
        red_hold_event()

    # check how the green button is pressed
    green_b = checkButton(green_button)
    if green_b == 1:
        green_click_event()
    if green_b == 2:
        green_double_click_event()
    if green_b == 3:
        green_hold_event()

    if not alarm_state:
        if(beeper.duty() != 0):
            beeper.duty(0)  # turn it off then
        draw_status_screen(oled)
        oled.show()
    else:  # alarm is on
        if(time.ticks_diff(time.ticks_ms(), alarm_sound_time) > 1000):  # has it been a second?
            beeper.duty(512)  # turn it on
        if(time.ticks_diff(time.ticks_ms(), alarm_sound_time) > 2000):
            beeper.duty(0)  # turn it on
            alarm_sound_time = time.ticks_ms()

    # check for nrf24 packages
    if radio.any():  # check if package is recieved
        radio_timeout_time = time.ticks_ms()
        radio_timedout = False
        # bool and char in arduino are represented as unsighned char with python type int for some reason, hence the usage of the two b's in the format
        payload = radio.recv()
        data = struct.unpack(struct_format, payload)
        info = list(data)  # but the data into a list
        print(info)
        # convert the numeric value of the state to the char value
        char = chr(info[2])
        info[1] = float("{:.2f}".format(info[1]))
        # info[2] = float("{:.2f}".format(info[2]))
        if(client is not None):
            try:
                client.publish(topic_pub, payload)
            except OSError as e:
                print("failed to send MQTT message")
        # convert the value from a char to a string representing the state
        if char == 'D':
            info[2] = "Disabled"
        elif char == 'E':
            info[2] = "Enabled"
        elif char == 'W':
            info[2] = "Waiting"
        else:
            info[2] = "UNKNOWN"
        latest_values = info[1:]  # get the values that need presentation
        if info[1] > 35 or info[0] == 1:  # temp too high or alarm
            alarm_state = True
            if info[1] > 35:  # temp too high
                text = "!!TOO HOT:{}C!!".format(info[1])
                draw_alarm_screen(oled, text, warning)
            else:  # alarm
                text = "!!CAT DETECTED!!"
                draw_alarm_screen(oled, text, cat)
        oled.show()  # show the buffer on the oled screen

    # check for mqtt messages
    if(client is not None):
        try:
            client.check_msg()
        except Exception:
            client = None

    # check for timeout
    if time.ticks_diff(time.ticks_ms(), radio_timeout_time) > (radio_timeout_delay * 1000):
        radio_timedout = True
        latest_values = [None, None]
    else:
        radio_timedout = False
# ================================================================
