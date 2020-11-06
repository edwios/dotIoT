import time
from machine import Pin, UART
import select
import secrets

DEBUG=True

DEFAULT_MESHNAME = secrets.DEFAULT_MESHNAME
DEFAULT_MESHPWD = secrets.DEFAULT_MESHPWD
SSID = secrets.SSID
PASS = secrets.PASS

DEFAULT_DSTADDR = "FFFF"
DEFAULT_OPCODE  = "D0"
DEFAULT_PARS    = "010000"

m_uart = UART(2, tx=18, rx=4)                         # init with given baudrate
m_uart.init(115200,bits=8,parity=None,stop=1,timeout=10)


poll = select.poll()
poll.register(m_uart, select.POLLIN)

def _send_command(cmd='AT'):
    if DEBUG: print("DEBUG: Sending %s to BLE Module" % cmd)
    m_uart.write(cmd + '\r\n')
    time.sleep(0.3)

def send_command(cmd):
    command = 'AT+'+cmd
    _send_command(command)

def checkBLEModule():
    _send_command()
    if not expect_reply():
        print("ERROR: Cannot get in touch with BLE module!")

def setMeshParams(name=DEFAULT_MESHNAME, pwd=DEFAULT_MESHPWD):
    send_command('MESHNAME=' + name)
    if not expect_reply('OK'):
        print("ERROR in setting Mesh Name")
        return False
    send_command('MESHPWD=' + pwd)
    if not expect_reply('OK'):
        print("ERROR in setting Mesh Password")
        return False
    return True    

def expect_reply(reply='OK'):
    rpy = getReply(5)
    if rpy is None:
        return False
    for i in rpy:
        if i == reply:
            return True
    return False

def getReply(timeout=10):
    events = poll.poll(timeout)
    data = ''
    while (len(events) > 0):
        events = poll.poll(timeout)
        for file in events:
            # file is a tuple
            if file[0] == m_uart:
                ch = m_uart.read(1)
                #print('Got ', ch)
                data = data + chr(ch[0])

    if data is not '':
        # Show the byte as 2 hex digits then in the default way
        if DEBUG: print("DEBUG: received from BLE module: %s " % data)
        #print(data)
        reply = []
        lines = data.split('\r\n')
        for l in lines:
            if l is not '':
                reply.append(l)
        if DEBUG: print("DEBUG: received %d lines of text as %s" % (len(reply), reply))
        return reply

def mesh_send(dst=0x00, cmd=0xd0, data=[]):
    length = len(data)
    atcommand = 'SEND={:x},{:d},{:02x}'.format(dst, length+1, cmd)
    for d in data:
        atcommand = atcommand + '{:02x}'.format(d)
    send_command(atcommand)
    if not expect_reply('OK'):
        print("ERROR in sending to mesh")
        return False
    return True    

def mesh_send_asc(dst, cmd, data):
    length = len(data)>>1
    atcommand = 'SEND={:s},{:s},{:s}{:s}'.format(dst, str(length), cmd, data)
    print("Sending to UART: %s" % atcommand)
    send_command(atcommand)
    if not expect_reply('OK'):
        print("ERROR in sending to mesh")
        return False
    return True

def _test_mesh_send(dst=0x00, cmd=0xd0, data=[]):
    length = len(data)
    atcommand = 'SEND={:0x},{:d},'.format(dst, length+1)
    atcommand = atcommand + chr(cmd)
    for d in data:
        atcommand = atcommand + chr(d)
    send_command(atcommand)
    if not expect_reply('OK'):
        print("ERROR in sending to mesh")
        return False
    return True    

checkBLEModule()
atcmd = ''
Opcode = ''
Meshname = input('Mesh name [%s]?' % DEFAULT_MESHNAME)
if Meshname == '': Meshname = DEFAULT_MESHNAME
Meshpass = input('Mesh password [%s]?' % DEFAULT_MESHPWD)
if Meshpass == '': Meshpass = DEFAULT_MESHPWD
ans = input('Direct AT command test [Y/n]?')
if ans == 'Y' or ans == 'y' or ans == '':
    print('Direct mode, enter "end" to end')
    setMeshParams(name=Meshname, pwd=Meshpass)
    while atcmd is not 'end':
        atcmd = input('AT line: [FFFF,4,D0010000]')
        if atcmd == '': atcmd = 'AT+SEND=FFFF,4,D0010000'
        if atcmd == 'end': break
#        atcmd = 'SEND=' + atcmd
#        send_command(atcmd)
        _send_command(atcmd)
        getReply(6)
        time.sleep(1)
        getReply(3)
else:
    setMeshParams(name=Meshname, pwd=Meshpass)
    while Opcode is not 'FF':
        print('Interactive mode, enter "FF" as Op code to end')
        # Start input node
        Dstdev = input('Dest addr [%s]?' % DEFAULT_DSTADDR)
        if Dstdev == '': Dstdev = DEFAULT_DSTADDR
        if Dstdev[0] == 'r' or Dstdev[0] == 's':
            if Dstdev[0] == 'r':    # Raw AT line, send it as is
                atcmd = Dstdev[1:]
                _send_command(atcmd)
            else:
                atcmd = 'AT+SEND=' + Dstdev[1:]
                _send_command(atcmd)
        else:
            Opcode = input('Op code [%s]?' % DEFAULT_OPCODE)
            if Opcode == 'FF': break
            if Opcode == '': Opcode = DEFAULT_OPCODE
            Pars = input('Pars [%s]' % DEFAULT_PARS)
            if Pars == '': Pars = DEFAULT_PARS
            print('Sending to device %s with Opcode %s and Pars %s' % (Dstdev, Opcode, Pars))
            mesh_send_asc(dst=Dstdev, cmd=Opcode, data=Pars)
        getReply(3)
        time.sleep(1)
        getReply(3)


#send_command('SEND=7,10,e01102ffff')
#mesh_send(dst=0x07, cmd=0xe0, data=[0xff, 0xff])
#mesh_send(dst=0x07, cmd=0xd3, data=[0x03])
#_test_mesh_send(dst=0x07, cmd=0xd3, data=[0x11, 0x02, 0x03])
'''
lt = time.time()
while (time.time() - lt) < 10:
    getReply(3)
    time.sleep(0.25)
'''
