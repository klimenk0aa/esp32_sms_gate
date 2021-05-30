# This is script that run when device boot up or wake from sleep.

import micropython

micropython.alloc_emergency_exception_buf(300)
import network
import machine
import time


#sta_if=network.WLAN(network.STA_IF)
#sta_if.active(1)
#sta_if.connect('MTK', 'tr010101010')


    
        
pin = machine.Pin(5, machine.Pin.OUT)
pin.value(0)
time.sleep_ms(500)
pin.value(1)

lan=network.LAN(mdc=machine.Pin(23), mdio=machine.Pin(18), power=machine.Pin(15), phy_addr = 1, phy_type=network.PHY_LAN8720)
lan.active(True)

time.sleep_ms(3000)
print(lan.ifconfig())



