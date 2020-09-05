#!/usr/bin/env python3

import sdnotify
from sys import exit
from os import system
import netifaces
from atm90e26 import atm90e26
import time
import datetime
import TimerLoop
import Backgrounder
import json
from influxdb import InfluxDBClient
import Lights
import paho.mqtt.client as mqtt


base_config = {
    'upload_period': 30,
    'notify_period': 60,
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
    'influx': {
        'do': False,
        'database': 'powerdemo',
        #'user': 'bloop',
        #'password': 'fill_this_in',
        'port': 8086,
        'host': 'ec2-34-220-91-92.us-west-2.compute.amazonaws.com',
    },
    'mqtt': {
        'do': True,
        "host": "35.236.54.162",
        "topic": "david/powermeter",
        #"user": "bloop",
        #"password": "fill_this_in",
    },
    'stats': {
        'max_push_errors': 10,
    }
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


def iSetup(cfg):
    c = cfg['influx']
    i = None
    if c['do']:
        i = InfluxDBClient(c['host'],
                           c['port'],
                           c['user'],
                           c['password'],
                           c['database'])

    return i


def mSetup(cfg):
    c = cfg['mqtt']
    m = None
    if c.get('do',False):
        m = mqtt.Client('powerclient')
        m.username_pw_set(cfg['mqtt']['user'],cfg['mqtt']['password'])
    return m


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
    sdn = sdnotify.SystemdNotifier()
    cfg['sdnotify'] = sdn
    sdn.notify('READY=1')

    i = iSetup(cfg)
    cfg['iconn'] = i
    m = mSetup(cfg)
    cfg['mconn'] = m

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
            print('Urms',sdata['Urms'])
        if 'Pmean' in sdata:
            print('Pmean',sdata['Pmean'])

        return sdata
    except Exception as e:
        print('well, that didn\'t work, because: {0}'.format(repr(e)))
        return None




class CapHandlers(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.cfg['tempdata'] = {}
        self.push_errors = 0;
        self.readingCount = 0
        self.pushCount = 0

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
        data = readSensor(self.cfg)
        self.stripUnwantedData(data)
        self.cfg['tempdata'][ts_sec_ms] = data
        self.cfg['lights'].set(self.readingCount & 0x1,
                               self.pushCount& 0x1)
        self.readingCount += 1

    def dataToArray(self, d):
        names = self.cfg['sensor_params']['vars']
        rdata = []
        for timestamp in sorted(d):
            values = [ d[timestamp][n]['value'] for n in names]
            rdata.append([timestamp] + values)
        return rdata


    def doIPush(self, name, now):
        if self.cfg['iconn'] is not None:
            try:
                tdata = self.cfg['tempdata']

                def oneWay(tdata):
                    odata = []
                    for ts in tdata:
                        tdatum = tdata[ts]
                        for vname in tdatum:
                            vval = tdatum[vname]['value']
                            odatum = {
                                'measurement': vname,
                                'time': datetime.datetime.utcfromtimestamp(ts),
                                'fields': { 
                                    'value': vval,
                                }
                            }
                            odata.append(odatum)
                    tags = {
                        'source': 'daves_power_meter',
                        'afe': 'atm90e26',
                    }
                    # print(odata)
                    res = self.cfg['iconn'].write_points(odata,tags=tags)
                    return res


                def anotherWay(tdata):
                    odata = []
                    for ts in tdata:
                        tdatum = tdata[ts]
                        fields = { k : v['value'] for (k,v) in tdatum.items() }
                        odatum = {
                            'measurement': 'meter0',
                            'time': datetime.datetime.utcfromtimestamp(ts),
                            'fields': fields,
                        }

                        odata.append(odatum)
                    tags = {
                        'source': 'daves_power_meter',
                        'afe': 'atm90e26',
                    }
                    res = self.cfg['iconn'].write_points(odata,tags=tags,database='powerdemo2')
                    return res


                res1 = anotherWay(tdata)
                if not res1:
                    print('anotherWay post error',res1)

                res0 = oneWay(tdata)
                if res0:
                    self.cfg['tempdata'] = {}
                    self.push_errors = 0
                    self.pushCount += 1
                else:
                    self.push_errors += 1
                    print('post error',res)

            except Exception as e:
                self.push_errors += 1
                print('EXCEPTION')
                print(e)
        if self.push_errors > self.cfg['stats']['max_push_errors']:
            exit(-1)


    def watchdog(self, name, now):
        if True:
            print('watchdog ping')
            self.cfg['sdnotify'].notify('STATUS=Push_Errors is {}'.format(self.push_errors))
            self.cfg['sdnotify'].notify('WATCHDOG=1')


    def doMPush(self, name, now):
        if self.cfg['mconn'] is not None:
            c = self.cfg['mconn']
            try:
                tdata = self.cfg['tempdata']
                odata = []
                for ts in tdata:
                    tdatum = tdata[ts]
                    fields = { k : v['value'] for (k,v) in tdatum.items() }
                    odatum = {
                        'measurement': 'meter0',
                        'time': str(datetime.datetime.utcfromtimestamp(ts)),
                        'fields': fields,
                    }
                    odata.append(odatum)

                ofinal = {
                    'source': 'daves_power_meter',
                    'afe': 'atm90e26',
                    'data': odata,
                }
                c.connect(cfg['mqtt']['host'])
                pres = c.publish(cfg['mqtt']['topic'],json.dumps(ofinal))
                c.disconnect()
                self.push_errors = 0
                self.pushCount += 1
            except Exception as e:
                self.push_errors += 1
                print('EXCEPTION: {}'.format(repr(e)))
            if self.push_errors > self.cfg['stats']['max_push_errors']:
                exit(-1)



def mymain(cfg):

    ch = CapHandlers(cfg)
    te = TimerLoop.TimerLoop()

    te.addHandler(ch.takeReading,  cfg['read_period'])
    te.addHandler(ch.doIPush,      cfg['upload_period'])
    te.addHandler(ch.doMPush,      cfg['upload_period'])
    te.addHandler(ch.watchdog,     cfg['notify_period'])
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


