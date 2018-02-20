#!/usr/bin/env python3

from sys import exit
from os import system
from atm90e26 import atm90e26
import time
import ServerConnection
import TimerLoop
import Backgrounder
import json

base_config = {
    'upload_period': 30,
    'read_period': 5,
    'config_check_period': 7200,
    'ping_period': 900,
    'tick_length': 0.5,
    'sensor_params': { 
        'sample_count': 5,
        'cut_count': 1,
        'vars': [
            'Urms','Irms','Freq','Pmean','Qmean','Smean','PowerF','Pangle',
            'APenergy','ANenergy','RPenergy','RNenergy'
        ],
    },
    'max_consec_net_errs': 10,
    'mail_check_period': 7200,
    'bground_check_period': 5,
}


def synchronizeSystemClock():
    print('synchronizeSystemClock()')
    clock_is_set = False
    clock_attempts_remain = 3
    while not clock_is_set and clock_attempts_remain:
        setres = system('sudo ./setclock.py')
        if setres == 0:
            clock_is_set = True
        else:
            clock_attempts_remain -= 1
    if not clock_is_set:
        sys.exit(-1)


def pre_run():
    afe = atm90e26()
    afe.setup('spi')
    afe.reset()
    ser = '12345678'

    server_config = {
        'provisioning_token_path': './provisioning_token.json',
        'url_base': 'http://192.168.0.102:9090/pwrmon',
        'credentials_path': './credentials.json',
        'params_path': './device_params.json',
        'device_name': 'pipowermeter_proto_0',
        'device_type': 'atm90e26_i2c_meter',
        'device_serial': ser.encode('ascii'),
    }

    sconn = ServerConnection.ServerConnection(server_config)

    cfg = { k:base_config[k] for k in base_config }

    cfg['afe'] = afe
    cfg['sconn'] = sconn

    if False:
        synchronizeSystemClock()

    return cfg



def saneRead(cfg):

    def removeExtrema(array,cutcount = 1):
        array.sort()
        return array[cutcount:-cutcount]

    adata = []
    varnames = cfg['sensor_params']['vars']

    for i in range(cfg['sensor_params']['sample_count']):
        trydata = cfg['afe'].getRegs(varnames)
        adata.append(trydata)

    values = {}
    for varname in varnames:
        darray = [ x[varname]['value'] for x in adata ]
        no_extrema = removeExtrema(darray,cfg['sensor_params']['cut_count'])
        avg = sum(no_extrema) / len(no_extrema)
        # round to nearest thousandth -- this is actually to stop sending extra
        # long strings with no info in JSON
        avg = (int(avg * 10000) + 0.5) / 10000
        values[varname] = { 'value': avg }

    return values



def readSensor(cfg):
    try:
        sdata = saneRead(cfg)
        if 'Urms' in sdata:
            print(sdata['Urms'])
        if 'Pmean' in sdata:
            print(sdata['Pmean'])
        return sdata
    except Exception as e:
        print('well, that didn\'t work, because: {0}'.format(repr(e)))
        return None


def readSensor_old(cfg):
    print('readSensor()')

    try:
        sdata = cfg['afe'].getRegs(cfg['sensor_params']['vars'])
        if 'Urms' in sdata:
            print(sdata['Urms'])
        if 'Pmean' in sdata:
            print(sdata['Pmean'])

        return sdata

    except Exception as e:
        print('well, that didn\'t work, because: {0}'.format(repr(e)))
        return None




class CapHandlers(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.cfg['tempdata'] = {}

    # this removes some metadata from reading from the
    # meter that is nice for debug but the server has
    # no use for it
    def stripUnwantedData(self,din):
        for k in din:
            for v in ['raw','aname','addr']:
                if v in din[k]:
                    del din[k][v]

    def takeReading(self, name, now):
        ts_sec_ms = time.time()
        ts_sec = int(ts_sec_ms + 0.5)
        data = readSensor(self.cfg)
        self.stripUnwantedData(data)
        self.cfg['tempdata'][ts_sec] = data

    def is2xx(self, res):
        if res.status_code > 299 or res.status_code < 200:
            return False
        return True

    def doPush(self, name, now):
        res = self.cfg['sconn'].push(self.cfg['tempdata'])
        if self.is2xx(res):
            self.cfg['tempdata'] = {}
        print(res)

    def checkNetErrs(self, name, now):
        if self.cfg['sconn'].getStats()['consec_net_errs'] > self.cfg['max_consec_net_errs']:
            print('Network not working. I\'m going to kill myself and presumably systemd will restart me.')
            exit(-10)

    def doPing(self, name, now):
        res = self.cfg['sconn'].ping()

    def cfgCheck(self, name, now):
        self.cfg['sconn'].getParams(self.cfg)



class MessageHandler(object):
    def __init__(self,sconn):
        self.sconn = sconn
        self.backgrounder = Backgrounder.Backgrounder()
    def messageType(self, msg, t):
        mt = msg.get('type',None)
        if mt:
            return mt == t
        return false
    def checkNew(self, name, now):
        messages = self.sconn.getMail()
        for message in messages:
            if self.messageType(message,'shell_script'):
                self.backgrounder.startNew(message)
            elif self.messageType(message,'restart'):
                sys.exit(0)
    def checkComplete(self, name, now):
        count, reses = self.backgrounder.checkResults()
        if count:
            for msgid in reses:
                self.sconn.respondMail(msgid,reses[msgid])






def mymain(cfg):

    ch = CapHandlers(cfg)
    te = TimerLoop.TimerLoop()
    mh = MessageHandler(cfg['sconn'])

    te.addHandler(ch.doPing,       cfg['ping_period'])
    te.addHandler(ch.takeReading,  cfg['read_period'])
    te.addHandler(ch.doPush,       cfg['upload_period'])
    te.addHandler(ch.checkNetErrs, cfg['upload_period'])
    te.addHandler(ch.cfgCheck,     cfg['config_check_period'])
    te.addHandler(mh.checkNew,     cfg['mail_check_period'])
    te.addHandler(mh.checkComplete,cfg['bground_check_period'])
    te.run(cfg['tick_length'])


if __name__ == '__main__':
#    if True:
    try:
        cfg = pre_run();
        if cfg:
            mymain(cfg)
    except Exception as e:
        print('Whoops!',e)

