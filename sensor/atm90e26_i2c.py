#!/usr/bin/env python3

import time
from smbus import SMBus

def debugprint(*args, **kwargs):
    print( "atm90e26_i2c "+ ' '.join(map(str,args)), **kwargs)


class atm90e26_i2c(object):

    def __init__(self):
        self.bus = SMBus(1)
        self.addr = 0x32
        self.atm90e26_addrs = {
            'SoftReset'    : { 'addr': 0x00, },
            'SysStatus'    : { 'addr': 0x01, },
            'FuncEn'       : { 'addr': 0x02, },
            'SagTh'        : { 'addr': 0x03, },
            'SmallPMod'    : { 'addr': 0x04, },
            'LastData'     : { 'addr': 0x06, },
            'CalStart'     : { 'addr': 0x20, },
            'PLconstH'     : { 'addr': 0x21, },
            'PLconstL'     : { 'addr': 0x22, },
            'Lgain'        : { 'addr': 0x23, },
            'Lphi'         : { 'addr': 0x24, },
            'Ngain'        : { 'addr': 0x25, },
            'Nphi'         : { 'addr': 0x26, },
            'PStartTh'     : { 'addr': 0x27, },
            'PNolTh'       : { 'addr': 0x28, },
            'QStartTh'     : { 'addr': 0x29, },
            'QNolTh'       : { 'addr': 0x2a, },
            'MMode'        : { 'addr': 0x2b, },
            'CS1'          : { 'addr': 0x2c, },
            'AdjStart'     : { 'addr': 0x30, },
            'Ugain'        : { 'addr': 0x31, },
            'IgainL'       : { 'addr': 0x32, },
            'IgainN'       : { 'addr': 0x33, },
            'Uoffset'      : { 'addr': 0x34, },
            'IoffsetL'     : { 'addr': 0x35, },
            'IoffsetN'     : { 'addr': 0x36, },
            'PoffsetL'     : { 'addr': 0x37, },
            'QoffsetL'     : { 'addr': 0x38, },
            'PoffsetN'     : { 'addr': 0x39, },
            'QoffsetN'     : { 'addr': 0x3a, },
            'CS2'          : { 'addr': 0x3b },

            'APenergy' : { 'addr': 0x40, 'prec': 0.1, 'unit': 'kJ'}, 
            'ANenergy' : { 'addr': 0x41, 'prec': 0.1, 'unit': 'kJ'},
            'ATenergy' : { 'addr': 0x42, 'prec': 0.1, 'unit': 'kJ'},
            'RPenergy' : { 'addr': 0x43, 'prec': 0.1, 'unit': 'kJ'}, 
            'RNenergy' : { 'addr': 0x44, 'prec': 0.1, 'unit': 'kJ'},
            'RTenergy' : { 'addr': 0x45, 'prec': 0.1, 'unit': 'kJ'},
            'EnStatus' : { 'addr': 0x46, },
            'Irms'     : { 'addr': 0x48, 'prec': 0.001, 'unit': 'A'},
            'Urms'     : { 'addr': 0x49, 'prec': 0.01, 'unit': 'V'},
            'Pmean'    : { 'addr': 0x4a, 'prec': 0.001, 'sgn': 'complement', 'unit': 'kW'},
            'Qmean'    : { 'addr': 0x4b, 'prec': 0.001, 'sgn': 'complement', 'unit': 'kVAR'},
            'Freq'     : { 'addr': 0x4c, 'prec': 0.01, 'unit': 'Hz'},
            'PowerF'   : { 'addr': 0x4d, 'sgn': 'msb', 'prec': 0.001, },
            'Pangle'   : { 'addr': 0x4e, 'prec': 0.1, 'sgn': 'msb', 'unit': 'deg'},
            'Smean'    : { 'addr': 0x4f, 'prec': 0.001, 'sgn': 'complement', 'unit': 'kVA'},
            'Irms2'    : { 'addr': 0x68, 'prec': 0.001, 'unit': 'A'},
            'Pmean2'   : { 'addr': 0x6a, 'prec': 0.001, 'sgn': 'complement', 'unit': 'kW'},
            'Qmean2'   : { 'addr': 0x6b, 'prec': 0.001, 'sgn': 'complement', 'unit': 'kVAR'},
            'PowerF2'  : { 'addr': 0x6d, 'sgn': 'msb', 'prec': 0.001, },
            'Pangle2'  : { 'addr': 0x6e, 'prec': 0.1, 'sgn': 'msb', 'unit': 'deg'},
            'SmeanF'   : { 'addr': 0x4f, 'prec': 0.001, 'sgn': 'complement', 'unit': 'kVA'},
        }
        self.atm90e26_reverse_addrs = {}
        for name in self.atm90e26_addrs:
            self.atm90e26_reverse_addrs[self.atm90e26_addrs[name]['addr']] = name

        self.calibvals = {
            'funcen': 0x0,

            'calibration': [
                ('PLconstH', 0x1c),
                ('PLconstL', 0xa90e),
                ('Lgain',    0x0),
                ('Lphi',     0x0),
                ('Ngain',    0x0),
                ('Nphi',     0x0),
                ('PStartTh', 0x8bd),
                ('PNolTh',   0x0),
                ('QStartTh', 0xaec),
                ('QNolTh',   0x0),
                ('MMode',    0x9422 & ~0xe000), # switch to 4x on current sense amp
             ],

            'adjustment': [
                ('Ugain',    14949),
                ('IgainL',   0x8d88),
                ('IgainN',   0x0),
                ('Uoffset',  0x0),
                ('IoffsetL', 0x0),
                ('IoffsetN', 0x0),
                ('PoffsetL', 0x0),
                ('QoffsetL', 0x0),
                ('PoffsetN', 0x0),
                ('QoffsetN', 0x0),
            ],
        }

        self.magic = {
            'reset': 0x789a,
            'cal_mode': 0x5678,
            'check_mode': 0x8765,
        }




    def reset(self):

        def writeBunch(self, pairs):
            chk_l = 0
            chk_h = 0
            regnames = []
            for regpair in pairs:
                if False:
                    cs1_afe = self.getReg('CS1')
                    debugprint('CS1: {:04x}'.format(cs1_afe['raw']))

                vn = regpair[0]
                regnames.append(vn)
                wrval = regpair[1]

                # increment the checksum calculation
                wrv_l = wrval & 0xff
                wrv_h = (wrval >> 8) & 0xff
                chk_h ^= wrv_h
                chk_h ^= wrv_l
                chk_l += wrv_h
                chk_l += wrv_l

                self._startWrite(vn, wrval)
                time.sleep(0.01)
                res0 = self.getReg(vn)
                time.sleep(0.01)
                if not res0 or res0['raw'] != wrval:
                    debugprint('[{}] wrote: {:04x} got {:04x}'.format(vn, wrval,res0['raw']))

            chk_l &= 0xff
            debugprint('MY chk_h: {:02x} chk_l: {:02x}'.format(chk_h,chk_l))
            return (chk_h << 8) | chk_l


        debugprint('- Resetting atm90e26 chip and setting calibration registers.')

        self._startWrite('SoftReset', self.magic['reset'])
        time.sleep(0.5)

        if True:
            self._startWrite('CalStart', self.magic['cal_mode'])
            mychk = writeBunch(self, self.calibvals['calibration'])
            self._startWrite('CS1',mychk)
            self._startWrite('CalStart', self.magic['check_mode'])

        if True:
            self._startWrite('AdjStart', self.magic['cal_mode'])
            mychk = writeBunch(self, self.calibvals['adjustment'])
            self._startWrite('CS2',mychk)
            self._startWrite('AdjStart', self.magic['check_mode'])

        if False:
            cs1_afe = self.getReg('CS1')
            cs2_afe = self.getReg('CS2')
            debugprint('CS1: {:04x} CS2: {:04x}'.format(cs1_afe['raw'],cs2_afe['raw']))




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
            debugprint('- Error writing to i2c device.');
            debugprint(e)
            try:
                debugprint('- attempting to restart i2c')
                self.__init__()
                self.reset()
            except Exception as f:
                pass
        return False

    def _startWrite(self, aname, data):
        reginfo = self.atm90e26_addrs.get(aname,None)
        if not reginfo:
            return None

        try:
            addr = reginfo['addr']
            d1 = (data >> 8) & 0xff
            d0 = data & 0xff
            self.bus.write_i2c_block_data(self.addr,addr & ~0x80,[d1,d0])
            time.sleep(0.05)
            return True
        except Exception as e:
            debugprint('- Error writing to i2c device: {0}'.format(repr(e)))
            try:
                debugprint('- attempting to restart i2c')
                self.__init__()
                self.reset()
            except Exception as f:
                pass
        return False

    def _readState(self):
        tries = 10
        while tries:
            try:
                data = self.bus.read_i2c_block_data(self.addr, 1, 4)
                if data[0] == 0x12:
                    addr = data[1] & ~0x80; # address without msb
                    word = (data[2] << 8) | data[3]
                    return { 'addr': addr, 'word': word }
                else:
                    tries -= 1
                    time.sleep(0.01)
            except Exception as e:
                debugprint('Exception reading state: {0}'.format(e))
                tries -= 1;
                time.sleep(0.10)
                try:
                    self.__init__()
                except Exception as f:
                    pass
            debugprint('_readState tries: {0}'.format(tries))

        return None

    def _polishRead(self, rawres):
        if rawres:
            name = self.atm90e26_reverse_addrs.get(rawres['addr'],'_unknown')
            fmt = self.atm90e26_addrs.get(name,None)
            word = rawres['word']
            val = word + 0
            unit = ''
            if fmt:
                sgn = fmt.get('sgn','unsigned')
                if sgn == 'unsigned':
                    pass
                elif sgn == 'complement':
                    if (word & 0x8000):
                        val -= 65535
                elif sgn == 'msb':
                    if (word & 0x8000):
                        word &= ~0x8000
                        val = -word

                prec = fmt.get('prec',1)
                val *= prec
                unit = fmt.get('unit','')
                return {
                    'addr': rawres['addr'],
                    'aname': name,
                    'raw': word,
                    'value': val,
                    'unit': unit
                }
        return None


    def getReg(self, aname):
        tries =10
        while tries:
            reqaddr = self._startRead(aname)
            if reqaddr:
                time.sleep(0.001)
                res0 = self._readState()
                lastaddr = self._startRead('LastData')
                if lastaddr:
                    time.sleep(0.001)
                    res1 = self._readState()
                    if res1:
                        a0match = res0['addr'] == reqaddr
                        a1match = res1['addr'] == self.atm90e26_addrs['LastData']['addr']
                        vmatch  = res0['word'] == res1['word']
                        if a0match and a1match and vmatch:
                            return self._polishRead(res0)
                        else:
                            if not a0match:
                                debugprint('Request  return addr {:02x} does not match requested {:02x}'.format(res0['addr'],reqaddr))
                            if not a1match:
                                debugprint('LastData return addr {:02x} does not match requested {:02x}'.format(res1['addr'],self.atm90e26_addrs['LastData']['addr']))
                            if not vmatch:
                                debugprint('Read value {:04x} does not match LastData value {:04x}'.format(res0['word'],res1['word']))
            else:
                debugprint("no reqaddr. Maybe {0} isn't right?".format(aname))
            tries -= 1
            debugprint('getReg tries: {0}'.format(tries))
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
        r.reset()

    while True:
        x = r.getRegs(['Freq','Urms','Irms','Pmean','SysStatus','CS1','CS2'])
        debugprint(json.dumps(x,indent=2,sort_keys=True))
        time.sleep(1)



