from neopixel import NeoPixel
from utime import sleep
import utime
import network
import usocket
import ustruct

nic = network.WLAN(network.STA_IF)
nic.active(True)
nic.connect('Plusle', '09221997')
print('Connected to Plusle')
print(nic.ifconfig())

NEOPIXEL_PIN = 0
NUMBER_PIXELS = 60

strip = NeoPixel(machine.Pin(NEOPIXEL_PIN), NUMBER_PIXELS)

def cnc_connect():
    sock = usocket.socket()
    addr = usocket.getaddrinfo('192.168.33.101', 9001)[0][-1]
    sock.connect(addr)
    
    return sock

sock = cnc_connect()
alarm_flag = True
while True:
    try:
        # update color
        sock.send(b'\x00')
        colors = sock.recv(3)
        colors = ustruct.unpack('>BBB', colors)
        
        # update alarm time
        sock.send(b'\x01')
        alarm_str = sock.recv(5).decode()
        alarm_hr = int(alarm_str[0:2])
        alarm_mn = int(alarm_str[3:5])
    except Exception as ex:
        print(ex)
        print('Connection lost')
        sock.close()
        sleep(5)
        sock = cnc_connect()
        continue

    _, _, _, hr, mn, _, _, _ = utime.localtime()

    if hr == alarm_hr and mn == alarm_mn:
        for i in range(NUMBER_PIXELS):
            if alarm_flag:
                strip[i] = colors
            else:
                strip[i] = (0, 0, 0)
                
        alarm_flag = not alarm_flag
    else:
        # normal on
        for i in range(NUMBER_PIXELS):
            strip[i] = colors
    strip.write()
