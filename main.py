import esp32
import gc
import sim800l
from machine import Timer
import uping
import time


from MicroWebSrv2 import *

def host_ping(host):
    res = ""
    msg = 'host "' + host + '" does not ping'
    try:
        ping_res = uping.ping(host, count=4, timeout=3000, interval=10, quiet=True, size=64)
        ping_stat = ping_res[1] / ping_res[0]
        if ping_stat < 0.75:
            time.sleep_ms(5000)
            ping_res2 = uping.ping(host, count=10, timeout=5000, interval=10, quiet=True, size=64)
            ping_stat2 = ping_res[1] / ping_res[0]
            if ping_stat2 < 0.75:
                res = msg
                sms.send_sms_u('79280399723', 'router не пингуется')
    except:
        res = msg
        sms.send_sms_u('79280399723', 'router не пингуется')
    print(res)



sms = sim800l.SIM800L(1)
sms.setup()

tim0 = Timer(0)
tim0.init(period=60000, mode=Timer.PERIODIC, callback=lambda t: host_ping('192.168.89.1'))

@WebRoute(GET, '/ping')
def RequestHandlerPing(microWebSrv2, request):
    request.Response.ReturnOk("pong")

@WebRoute(GET, '/cpu_temp')
def RequestHandlerCPUTemp(microWebSrv2, request):
    tf = esp32.raw_temperature()
    tc = (tf-32.0)/1.8
    request.Response.ReturnOk(str(tc))

@WebRoute(GET, '/mem_info')
def RequestHandlerMemFree(microWebSrv2, request):
    mem_info = gc.mem_free()
    request.Response.ReturnOk(str(mem_info))

@WebRoute(GET, '/battery')
def RequestHandlerBattery(microWebSrv2, request):
    data = sms.battery_charge()
    request.Response.ReturnOk(str(data))

@WebRoute(GET, '/network_name')
def RequestHandlerNetworkName(microWebSrv2, request):
    try:
        data = sms.command('AT+CSPN?\n',3,3000)
        request.Response.ReturnOk(data)
    except:
        request.Response.ReturnOk("fail")

@WebRoute(GET, '/signal_strength')
def RequestHandlerSignal(microWebSrv2, request):
    try:
        data = sms.signal_strength()
        #print(data)
        request.Response.ReturnOk(str(data))
    except:
        request.Response.ReturnOk("fail")

@WebRoute(POST, '/send_sms/')
def RequestHandlerSendSms(microWebSrv2, request):
    data = request.GetPostedJSONObject()
    print(data)
    tel = data['tel']
    text = data['text']
    sms.send_sms_u(tel, text)
    request.Response.ReturnOk("OK")
        #request.Response.ReturnOkJSON({
        #    'tel'    : tel,
        #    'text'   : text,
        #    'status' : 'OK'
        #})




mws2 = MicroWebSrv2()
mws2.SetEmbeddedConfig()
mws2.BindAddress = ('0.0.0.0', 12345)
mws2.BufferSlotsCount = 4
mws2.StartManaged()

while mws2.IsRunning :
    sleep(1)



