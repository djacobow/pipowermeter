#!/usr/bin/env python3

import time
from smbus import SMBus



class atm90e26_i2c(object):

    def __init__(self):
        self.bus = SMBus(1)
        self.addr = 0x32
        self.atm90e26_addrs = {
            'reset'    : { 'addr': 0x00, },
            'status'   : { 'addr': 0x01, },
            'funcen'   : { 'addr': 0x02, },
            'sagthr'   : { 'addr': 0x03, },
            'smallmod' : { 'addr': 0x04, },
            'lastdat'  : { 'addr': 0x06, },
            'plconsth' : { 'addr': 0x21, },
            'plconstl' : { 'addr': 0x22, },
            'calstart' : { 'addr': 0x20, },
            'mmode'    : { 'addr': 0x2b, },
            'adjstart' : { 'addr': 0x30, },
            'ugain'    : { 'addr': 0x31, },
            'igainl'   : { 'addr': 0x32, },
            'igainn'   : { 'addr': 0x33, },
            'apenergy' : { 'addr': 0x40, 'prec': 0.1, 'unit': 'kJ'}, 
            'anenergy' : { 'addr': 0x41, 'prec': 0.1, 'unit': 'kJ'},
            'rpenergy' : { 'addr': 0x43, 'prec': 0.1, 'unit': 'kJ'}, 
            'rnenergy' : { 'addr': 0x44, 'prec': 0.1, 'unit': 'kJ'},
            'enstatus' : { 'addr': 0x46, },
            'irmsl'    : { 'addr': 0x48, 'prec': 0.001, 'unit': 'A'},
            'urms'     : { 'addr': 0x49, 'prec': 0.01, 'unit': 'V'},
            'pmeanl'   : { 'addr': 0x4a, 'prec': 0.001, 'sgn': 'complement', 'unit': 'kW'},
            'qmeanl'   : { 'addr': 0x4b, 'prec': 0.001, 'sgn': 'complement', 'unit': 'kVAR'},
            'freq'     : { 'addr': 0x4c, 'prec': 0.01, 'unit': 'Hz'},
            'pfl'      : { 'addr': 0x4d, 'sgn': 'msb', 'prec': 0.001, },
            'panglel'  : { 'addr': 0x4e, 'prec': 0.1, 'sgn': 'msb', 'unit': 'deg'},
            'smeanl'   : { 'addr': 0x4f, 'prec': 0.001, 'sgn': 'complement', 'unit': 'kVA'},
            'irmsn'    : { 'addr': 0x68, 'prec': 0.001, 'unit': 'A'},

        }

        self.atm90e26_reverse_addrs = {}
        for name in self.atm90e26_addrs:
            self.atm90e26_reverse_addrs[self.atm90e26_addrs[name]['addr']] = name


    def _startRead(self, aname):
        reginfo = self.atm90e26_addrs.get(aname,None)
        if not reginfo:
            return None

        try:
            addr = reginfo['addr']
            self.bus.write_i2c_block_data(self.addr,addr | 0x80,[0,0])
            #time.sleep(0.5)
            return reginfo['addr'] 
        except Exception as e:
            print('- Error writing to i2c device.');
            print(e)
            try:
                print('- attempting to restart i2c')
                self.__init__()
            except Exception as f:
                pass
        return False

    def _startWrite(self, aname, data):
        reginfo = self.atm90e26_addrs.get(aname,None)
        if not reginfo:
            return None

        try:
            d1 = (data >> 8) & 0xff
            d0 = data & 0xff
            addr = reginfo['addr']
            self.bus.write_i2c_block_data(self.addr,addr & ~0x80,[d1,d0])
            #time.sleep(0.05)
            return True
        except Exception as e:
            print('- Error writing to i2c device.');
            print(e)
            try:
                print('- attempting to restart i2c')
                self.__init__()
            except Exception as f:
                pass
        return False

    def _readState(self):
        done = False
        count = 10
        while not done and count:
            try:
                data = self.bus.read_i2c_block_data(self.addr, 1, 4)
                #print("rdata {:02X} {:02X} {:02X} {:02X}".format(data[0],data[1],data[2],data[3]))
                if data[0] == 0x12:
                    done = True
                    addr = data[1] & ~0x80; # address without msb
                    name = self.atm90e26_reverse_addrs.get(data[1],'_unknown')
                    fmt = self.atm90e26_addrs.get(name,None)
                    dword = (data[2] << 8) | data[3]
                    dval = dword + 0
                    unit = ''
                    if fmt:
                        sgn = fmt.get('sgn','unsigned')
                        if sgn == 'unsigned':
                            pass
                        elif sgn == 'complement':
                            if (dword & 0x8000):
                                dval -= 65535
                        elif sgn == 'msb':
                            if (dword & 0x8000):
                                dword &= ~0x8000
                                dval = -dword

                        prec = fmt.get('prec',1)
                        dval *= prec
                        unit = fmt.get('unit','')


                    return {
                        'addr': data[1],
                        'aname': name,
                        'raw': (data[2] << 8) | data[3],
                        'value': dval,
                        'unit': unit
                    }
                else:
                    count -= 1;
                    time.sleep(0.025)
            except Exception as e:
                print(e)
                count -= 1;
                time.sleep(0.10)
                try:
                    self.__init__()
                except Exception as f:
                    pass
        return None

    def getReg(self, aname):
        #print("getReg()")
        tries = 50
        res = None
        while tries:
            #print("gonna to another _startRead")
            reqaddr = self._startRead(aname)
            if reqaddr:
                res = self._readState()
                if res['addr'] == reqaddr:
                    return res
                else:
                    print("address return mismatch. Asked for {:02x} and got {:02x}".format(reqaddr, res['addr']))
            else:
                print("no reqaddr")
            tries -= 1

        return None

    def getRegs(self, names):
        res = {}
        for name in names:
            res[name] = self.getReg(name)
        return res




if __name__ == '__main__':
    import json
    r = atm90e26_i2c()

    if True:
        regs = [
            "status", "mmode", "adjstart", "calstart", "ugain", "igainl",
            "urms", "irmsl", "freq", "pmeanl", "qmeanl", "pfl", "panglel",
            "apenergy", "anenergy", "rpenergy", "rnenergy", ]

        while True:
            x = r.getRegs(regs)
            print(json.dumps(x,indent=2,sort_keys=True))
            time.sleep(1)

    if False:
        x = r.getReg('urms')
        print(x)



