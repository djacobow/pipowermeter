#!/usr/bin/env python3

from sys import exit
from os import system
import netifaces
from atm90e26 import atm90e26
import time
import TimerLoop
import Backgrounder
import json
import goog
import Lights

base_config = {
    'upload_period': 30,
    'read_period': 5,
    'config_check_period': 7200,
    'tick_length': 0.5,
    'sensor_params': { 
        'sample_count': 5,
        'cut_count': 1,
        'vars': [
            'Urms','Irms','Freq','Pmean','Qmean','Smean','PowerF','Pangle',
            'APenergy','ANenergy','RPenergy','RNenergy'
        ],
    },
    'gsheet': {
        'do': True,
        'parent': '11EIJbrb8SA75A_SgIBAV6t8EWD8A1XiB',
        'period': 60,
        'max_push_errors': 10,
     },
}


def getIPaddrs():
    rv = {}
    for n in netifaces.interfaces():
        adata = netifaces.ifaddresses(n)
        rv[n] = { t: adata.get(t,[{}])[0].get('addr',None) for t in (netifaces.AF_LINK,netifaces.AF_INET,netifaces.AF_INET6) }
    return rv


def getSerial():
    cpuserial = "0000000000000000"
    try:
        with open('/proc/cpuinfo','r') as fh:
            for line in fh:
                if line[0:6]=='Serial':
                    cpuserial = line[10:26]
    except:
        cpuserial = "ERROR000000000"
    return cpuserial


def gSetup(cfg):
    c = cfg['gsheet']
    g = None
    sheetid = None
    if c['do']:
        import goog
        import datetime
        g = goog.Googleizer()
        now = datetime.datetime.now()
        sname = 'Power Data ' + getSerial() + ' ' + now.isoformat()
        sheetid = g.createSheet(sname, c['parent'])

        headers = [ [ 'Device Serial', cfg['serial'] ] ]
        for ifn in cfg['ips']:
            if_header = [ 'if_name', ifn ]
            for atype in (netifaces.AF_LINK,netifaces.AF_INET,netifaces.AF_INET6):
                if_header.append(cfg['ips'][ifn][atype])
            headers.append(if_header)
        headers.append([])


        g.addRows(sheetid,headers)
        
        col_names = [ ['timestamp'] + cfg['sensor_params']['vars'] ]
        g.addRows(sheetid,col_names)
    return g, sheetid



def pre_run():
    afe = atm90e26()
    afe.setup('spi')

    cfg = { k:base_config[k] for k in base_config }

    local_overrides = json.load(open('./device_params.json'))
    for k in local_overrides:
        cfg[k] = local_overrides[k]

    if cfg.get('calibration',None) is not None:
        afe.loadCalibration(cfg['calibration'])

    afe.reset()

    cfg['lights'] = Lights.Lights()
    cfg['afe'] = afe
    cfg['serial'] = getSerial()
    cfg['ips'] = getIPaddrs()

    g, sheetid = gSetup(cfg)
    cfg['gconn'] = {
        'g': g,
        'id': sheetid,
    }

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
        avg = (round(avg,5))
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
        self.push_errors = 0;

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
        self.cfg['lights'].show(data['Pmean']['value'])


    def dataToArray(self, d):
        names = self.cfg['sensor_params']['vars']
        rdata = []
        for timestamp in sorted(d):
            values = [ d[timestamp][n]['value'] for n in names]
            rdata.append([timestamp] + values)
        return rdata

    def doGPush(self, name, now):
        if self.cfg['gconn'].get('g',None) is not None:
            try:
                rowdata = self.dataToArray(self.cfg['tempdata'])

                res = self.cfg['gconn']['g'].addRows(self.cfg['gconn']['id'], rowdata)
                if res and res.get('updates',None) and res['updates'].get('updatedCells',None):
                    self.cfg['tempdata'] = {}
                    self.push_errors = 0
                else:
                    print('Push error')
                    self.push_errors += 1
            except Exception as e:
                self.push_errors += 1
                print('EXCEPTION')
                print(e)
        if self.push_errors > self.cfg['gsheet']['max_push_errors']:
            exit(-1)





def mymain(cfg):

    ch = CapHandlers(cfg)
    te = TimerLoop.TimerLoop()

    te.addHandler(ch.takeReading,  cfg['read_period'])
    te.addHandler(ch.doGPush,      cfg['upload_period'])
    te.run(cfg['tick_length'])


if __name__ == '__main__':
#    if True:
    try:
        cfg = pre_run();
        if cfg:
            mymain(cfg)
    except Exception as e:
        print('Whoops!',e)
        import traceback
        import sys
        traceback.print_exc(file=sys.stdout)


