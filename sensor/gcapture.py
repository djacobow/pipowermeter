#!/usr/bin/env python3

from sys import exit
from os import system
from atm90e26 import atm90e26
import time
import TimerLoop
import Backgrounder
import json
import goog

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
     },
}


def gSetup(cfg):
    c = cfg['gsheet']
    g = None
    sheetid = None
    if c['do']:
        import goog
        import datetime
        g = goog.Googleizer()
        now = datetime.datetime.now()
        sname = 'Power Data ' + now.isoformat()
        sheetid = g.createSheet(sname, c['parent'])
        g.addRows(sheetid,[ ['timestamp' + cfg['sensor_params']['vars'] ])
    return g, sheetid


def pre_run():
    afe = atm90e26()
    afe.setup('spi')
    afe.reset()
    ser = '12345678'

    cfg = { k:base_config[k] for k in base_config }

    cfg['afe'] = afe

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


    def dataToArray(self, d):
        names = self.cfg['sensor_params']['vars']
        rdata = []
        for timestamp in d:
            values = [ d[timestamp][n]['value'] for n in names]
            rdata.append([timestamp] + values)
        return rdata

    def doGPush(self, name, now):
        if self.cfg['gconn'].get('g',None) is not None:
            try:
                rowdata = self.dataToArray(self.cfg['tempdata'])

                res = self.cfg['gconn']['g'].addRows(self.cfg['gconn']['id'], rowdata)
            except Exception as e:
                print(e)




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

