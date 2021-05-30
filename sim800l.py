# Driver for SIM800L module (using AT commands)


import machine
import time
import math

# kludge required because "ignore" parameter to decode not implemented
def convert_to_string(buf):
    try:
        tt =  buf.decode('utf-8').strip()
        return tt
    except UnicodeError:
        tmp = bytearray(buf)
        for i in range(len(tmp)):
            if tmp[i]>127:
                tmp[i] = ord('#')
        return bytes(tmp).decode('utf-8').strip()

class SIM800LError(Exception):
    pass

def check_result(errmsg,expected,res):
    if not res:
        res = 'None'
    #print(errmsg+res)
    if not expected == res and not res == 'None':
        raise SIM800LError('SIM800L Error {}  {}'.format(errmsg,res))


class SIM800L:

    def __init__(self,uartno):  # pos =1 or 2 depending on skin position
        self._uart = machine.UART(uartno, 115200, tx=17,rx=16)
        self.incoming_action = None
        self.no_carrier_action = None
        self.clip_action = None
        self._clip = None
        self.msg_action = None
        self._msgid = 0
        self.savbuf = None
        self.credit = ''
        self.credit_action = None

    def callback_incoming(self,action):
        self.incoming_action = action

    def callback_no_carrier(self,action):
        self.no_carrier_action = action

    def callback_clip(self,action):
        self.clip_action = action

    def callback_credit_action(self,action):
        self.credit_action = action

    def get_clip(self):
        return self._clip

    def callback_msg(self,action):
        self.msg_action = action

    def get_msgid(self):
        return self._msgid

    def command(self, cmdstr, lines=1, waitfor=500, msgtext=None):
        #flush input
        #print(cmdstr)
        while self._uart.any():
            self._uart.read()2
        self._uart.write(cmdstr)
        if msgtext:
            self._uart.write(msgtext)
        time.sleep_ms(waitfor)
        buf=self._uart.readline() #discard linefeed etc
        #print(buf)
        buf=self._uart.readline()
        #print(buf)
        if not buf:
            return None
        result = convert_to_string(buf)
        if lines>1:
            self.savbuf = ''
            for i in range(lines-1):
                buf=self._uart.readline()
                if not buf:
                    return result
                #print(buf)
                buf = convert_to_string(buf)
                if not buf == '' and not buf == 'OK':
                    self.savbuf += buf+'\n'
        return result

    def setup(self):
        self.command('ATE0\n')         # command echo off
        self.command('AT+CRSL=99\n')   # ringer level
        self.command('AT+CMIC=0,10\n') # microphone gain
        self.command('AT+CLIP=1\n')    # caller line identification
        self.command("AT+CSCS=\"UCS2\"\n",3,2000)
        self.command("AT+CMGF=0\n")
        self.command("AT+CSMP=17,167,0,8\n")
        self.command('AT+CALS=3,0\n')  # set ringtone
        self.command('AT+CLTS=1\n')    # enabke get local timestamp mode
        self.command('AT+CSCLK=0\n')   # disable automatic sleep

    def wakechars(self):
        self._uart.write('AT\n')        # will be ignored
        time.sleep_ms(100)

    def sleep(self,n):
        self.command('AT+CSCLK={}\n'.format(n))

    def sms_alert(self):
        self.command('AT+CALS=1,1\n')  # set ringtone
        time.sleep_ms(3000)
        self.command('AT+CALS=3,0\n')  # set ringtone

    def call(self,numstr):
        self.command('ATD{};\n'.format(numstr))

    def hangup(self):
        self.command('ATH\n')

    def answer(self):
        self.command('ATA\n')

    def set_volume(self,vol):
        if (vol>=0 and vol<=100):
            self.command('AT+CLVL={}\n'.format(vol))

    def signal_strength(self):
        result = self.command('AT+CSQ\n',3,3000)
        if result:
            params=result.split(',')
            if not params[0] == '':
                params2 = params[0].split(':')
                if params2[0]=='+CSQ':
                    x = int(params2[1])
                    if not x == 99:
                        return(math.floor(x/6+0.5))
        return -1

    def battery_charge(self):
        result = self.command('AT+CBC\n',3,1500)
        if result:
            params=result.split(',')
            if not params[0] == '':
                params2 = params[0].split(':')
                if params2[0]=='+CBC':
                    return int(params[2])/1000
        return 0


    def network_name(self):
        result = self.command('AT+CSPN?\n',3,2000)
        if result:
            params=result.split(',')
            if not params[0] == '':
                params2 = params[0].split(':')
                if params2[0]=='+CSPN':
                    names = params[2].split('"')
                    return names[1]
        return result


    def read_sms(self,id):
        result = self.command('AT+CMGR={}\n'.format(id),99)
        if result:
            params=result.split(',')
            if not params[0] == '':
                params2 = params[0].split(':')
                if params2[0]=='+CMGR':
                    number = params[1].replace('"',' ').strip()
                    date   = params[3].replace('"',' ').strip()
                    time   = params[4].replace('"',' ').strip()
                    return  [number,date,time,self.savbuf]
        return None

    def send_sms(self,destno,msgtext):
        result = self.command('AT+CMGS="{}"\n'.format(destno),99,5000,msgtext+'\x1A')
        if result and result=='>' and self.savbuf:
            params = self.savbuf.split(':')
            if params[0]=='+CUSD' or params[0] == '+CMGS':
                return 'OK'
        return result

    def send_sms_u(self, destno, msgtext):
        destno+="F"
        num = ''
        for i in range(len(destno)//2):
            aux = destno[i*2:i*2+2]
            num+= aux[1]+aux[0]
        char_map = {
            '0': '0030',
            '1': '0031',
            '2': '0032',
            '3': '0033',
            '4': '0034',
            '5': '0035',
            '6': '0036',
            '7': '0037',
            '8': '0038',
            '9': '0039',
            '<': '003c',
            '>': '003e',
            '[': '005b',
            ']': '005d',
            '{': '007b',
            '}': '007d',
            ';': '003b',
            ':': '003a',
            '^': '005e',
            '\'': '0027',
            '"': '0022',
            '№': '2116',
            ' ': '0020',
            '!': '0021',
            '#': '0023',
            '$': '0024',
            '%': '0025',
            '&': '0026',
            '(': '0028',
            ')': '0029',
            '*': '002a',
            '+': '002b',
            ',': '002c',
            '-': '002d',
            '.': '002e',
            '/': '002f',
            '=': '003d',
            '?': '003f',
            '@': '0040',
            'A': '0041',
            'B': '0042',
            'C': '0043',
            'D': '0044',
            'E': '0045',
            'F': '0046',
            'G': '0047',
            'H': '0048',
            'I': '0049',
            'J': '004a',
            'K': '004b',
            'L': '004c',
            'M': '004d',
            'N': '004e',
            'O': '004f',
            'P': '0050',
            'Q': '0051',
            'R': '0052',
            'S': '0053',
            'T': '0054',
            'U': '0055',
            'V': '0056',
            'W': '0057',
            'X': '0058',
            'Y': '0059',
            'Z': '005a',
            '\\': '005c',
            '^': '005e',
            '_': '005f',
            '`': '0060',
            'a': '0061',
            'b': '0062',
            'c': '0063',
            'd': '0064',
            'e': '0065',
            'f': '0066',
            'g': '0067',
            'h': '0068',
            'i': '0069',
            'j': '006a',
            'k': '006b',
            'l': '006c',
            'm': '006d',
            'n': '006e',
            'o': '006f',
            'p': '0070',
            'q': '0071',
            'r': '0072',
            's': '0073',
            't': '0074',
            'u': '0075',
            'v': '0076',
            'w': '0077',
            'x': '0078',
            'y': '0079',
            'z': '007a',
            '|': '007c',
            '~': '007e',
            'Ё': '0401',
            'А': '0410',
            'Б': '0411',
            'В': '0412',
            'Г': '0413',
            'Д': '0414',
            'Е': '0415',
            'Ж': '0416',
            'З': '0417',
            'И': '0418',
            'Й': '0419',
            'К': '041a',
            'Л': '041b',
            'М': '041c',
            'Н': '041d',
            'О': '041e',
            'П': '041f',
            'Р': '0420',
            'С': '0421',
            'Т': '0422',
            'У': '0423',
            'Ф': '0424',
            'Х': '0425',
            'Ц': '0426',
            'Ч': '0427',
            'Ш': '0428',
            'Щ': '0429',
            'Ъ': '042a',
            'Ы': '042b',
            'Ь': '042c',
            'Э': '042d',
            'Ю': '042e',
            'Я': '042f',
            'а': '0430',
            'б': '0431',
            'в': '0432',
            'г': '0433',
            'д': '0434',
            'е': '0435',
            'ж': '0436',
            'з': '0437',
            'и': '0438',
            'й': '0439',
            'к': '043a',
            'л': '043b',
            'м': '043c',
            'н': '043d',
            'о': '043e',
            'п': '043f',
            'р': '0440',
            'с': '0441',
            'т': '0442',
            'у': '0443',
            'ф': '0444',
            'х': '0445',
            'ц': '0446',
            'ч': '0447',
            'ш': '0448',
            'щ': '0449',
            'ъ': '044a',
            'ы': '044b',
            'ь': '044c',
            'э': '044d',
            'ю': '044e',
            'я': '044f',
            'ё': '0451'}

        if len(msgtext) < 60:
            msg_len = '{:02x}'.format(len(msgtext)*2)
            msg_body=''
            for s in msgtext:
                msg_body += char_map.get(s, "0021")
            header = "0011000B91"
            midle = "000897"
            pdu = header + num +midle + msg_len+msg_body+ "\x1a"
            prefix = "AT+CMGS=" +str((len(pdu)-4)//2+1) + "\r\n"

            self.command(prefix)
            result = self.command(pdu)
            if result and result=='>' and self.savbuf:
                params = self.savbuf.split(':')
                if params[0]=='+CUSD' or params[0] == '+CMGS':
                    return 'OK'
        else:
            header = "0041000C91"
            midle = "0008"
            segments_count = len(msgtext)//60 + bool(len(msgtext) % 60)
            count_aux = 0
            for i in range(segments_count):
                msgtext_ = msgtext[60*i: 60*(i+1)]
                counts = '{:02x}'.format(segments_count)
                count_number = '{:02x}'.format(i+1)
                msg_len = '{:02x}'.format(len(msgtext_)*2 + 6)
                msg_body=''
                for s in msgtext_:
                    msg_body += char_map.get(s, "0021")
                pdu = header + num + midle + msg_len + "05000300" + counts + count_number + msg_body+ "\x1a"
                prefix = "AT+CMGS=" +str((len(pdu)-4)//2+1) + "\r\n"
                #print(prefix)
                #print(pdu)
                #print('+++')
                result = self.command(prefix)
                print(result)
                result = self.command(pdu)
                print(result)
                if result and result=='>' and self.savbuf:
                    count_aux = count_aux + 1
                    #params = self.savbuf.split(':')
                time.sleep_ms(5000)
            #if params[0]=='+CUSD' or params[0] == '+CMGS':
            if result:
                return 'OK'
        return result


    def check_credit(self):
        self.command('AT+CUSD=1,"*100#"\n')


    def get_credit(self):
        return self.credit

    def delete_sms(self,id):
        self.command('AT+CMGD={}\n'.format(id),1)

    def date_time(self):
        result = self.command('AT+CCLK?\n',3)
        if result:
            if result[0:5] == "+CCLK":
                return result.split('"')[1]
        return ''

    def check_incoming(self):
        if self._uart.any():
            buf=self._uart.readline()
            # print(buf)
            buf = convert_to_string(buf)
            params=buf.split(',')
            if params[0] == "RING":
                if self.incoming_action:
                    self.incoming_action()
            elif params[0][0:5] == "+CLIP":
                params2 = params[0].split('"')
                self._clip = params2[1]
                if self.clip_action:
                    self.clip_action()
            elif params[0][0:5] == "+CMTI":
                self._msgid = int(params[1])
                if self.msg_action:
                    self.msg_action()
            elif params[0][0:5] == "+CUSD":
                if len(params)>1:
                    st = params[1].find('#')
                    en = params[1].find('.',st)
                    en = params[1].find('.',en+1)
                    if st>0 and en>0:
                        self.credit = '£'+params[1][st+1:en]
                        if self.credit_action:
                            self.credit_action()
            elif params[0] == "NO CARRIER":
                    self.no_carrier_action()


    # http get command using gprs
    def http_get(self,url,apn="giffgaff.com"):
        resp = None
        rstate = 0
        proto, dummy, surl = url.split("/", 2)
        is_ssl = 0
        if  proto == "http:":
            is_ssl = 0
        elif proto == "https:":
            is_ssl == 1
        else:
            raise ValueError("Unsupported protocol: " + proto)
        try:
            # open bearer context
            res = self.command('AT+SAPBR=3,1,"Contype","GPRS"\n')
            check_result("SAPBR 1: ",'OK',res)
            res = self.command('AT+SAPBR=3,1,"APN","{}"\n'.format(apn))
            check_result("SAPBR 2: ",'OK',res)
            res = self.command('AT+SAPBR=1,1\n',1,2000)
            check_result("SAPBR 3: ",'OK',res)
            # now do http request
            res = self.command('AT+HTTPINIT\n',1)
            check_result("HTTPINIT: ",'OK',res)
            res = self.command('AT+HTTPPARA="CID",1\n')
            check_result("HTTPPARA 1: ",'OK',res)
            res = self.command('AT+HTTPPARA="URL","{}"\n'.format(surl))
            check_result("HTTPPARA 2: ",'OK',res)
            res = self.command('AT+HTTPSSL={}\n'.format(is_ssl))
            check_result("HTTPSSL: ",'OK',res)
            res = self.command('AT+HTTPACTION=0\n')
            check_result("HTTPACTION: ",'OK',res)
            for i in range(20):  #limit wait to max 20 x readline timeout
                buf = self._uart.readline()
                if buf and not buf==b'\r\n':
                    buf = convert_to_string(buf)
                    #print(buf)
                    prefix,retcode,bytes = buf.split(',')
                    rstate = int(retcode)
                    nbytes = int(bytes)
                    break
            res = self.command('AT+HTTPREAD\n',1)
            buf = self._uart.read(nbytes)
            check_result("HTTPACTION: ",'+HTTPREAD: {}'.format(nbytes),res)
            if buf[-4:] == b'OK\r\n':  # remove final OK if it was read
                buf = buf[:-4]
            resp = Response(buf)
        except SIM800LError as err:
            print(str(err))
        self.command('AT+HTTPTERM\n',1) # terminate HTTP task
        self.command('AT+SAPBR=0,1\n',1) # close Bearer context
        return resp


    def test(self):
        r = self.http_get('http://exploreembedded.com/wiki/images/1/15/Hello.txt')
        print(r.text)

class Response:
    def __init__(self, buf, status = 200):
        self.encoding = "utf-8"
        self._cached = buf
        self.status = status
    def close(self):
        self._cached = None

    @property
    def content(self):
        return self._cached

    @property
    def text(self):
        return str(self.content, self.encoding)

    def json(self):
        import ujson
        return ujson.loads(self.content)




