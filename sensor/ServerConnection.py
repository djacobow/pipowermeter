
import string
import random
import requests
from urllib.parse import quote_plus
import json
import datetime
import socket
import os
import netifaces
import hashlib
import base64 as b64

# RPi only has Pi 3.4 which has no "secrets"
no_secrets = False
try:
    import secrets
except:
    import random
    no_secrets = True

DEBUG_AUTH = False

def dB(n,b):
    if DEBUG_AUTH:
        print('DBG ' + n + '\t:\t' + b64.b64encode(b).decode('ascii'))

class ServerConnection(object):
    def __init__(self, server_config):

        self.config = server_config
 
        if not self.config.get('credentials_path',None):
            raise Exception('credential_path_not_provided')
        if not self.config.get('url_base',None):
            raise Exception('server_url_base_not_provided')
        if not self.config.get('device_serial',None):
            raise Exception('device_serial_identifier_not_provided')

        def setIfNeeded(name,value):
            if not self.config.get(name,None):
                self.config[name] = value

        setIfNeeded('device_type','generic')
        setIfNeeded('post_url', self.config['url_base'] + '/device/push')
        setIfNeeded('ping_url', self.config['url_base'] + '/device/ping')
        setIfNeeded('params_url', self.config['url_base'] + '/device/params')
        setIfNeeded('mail_fetch_url', self.config['url_base'] + '/device/mbox/fetch')
        setIfNeeded('mail_post_url', self.config['url_base'] + '/device/mbox/respond')

        self.stats = {
            'consec_net_errs': 0,
            'push_attempts': 0,
            'push_failures': 0,
            'ping_attempts': 0,
            'ping_failures': 0,
        }
        self.non_override_keys = {
            'sconn': 1,
            'kconn': 1,
        }
        # return local IP. We'll get the public IP from the http request,
        # and there's no good reason to trust the device for that
        self.help = _Helpers()
        self.interfaces = self.help.myInterfaces()
        self.hostname = self.help.myHost()
        self.creds  = self._loadCredentials()


    def getStats(self):
        return { k:self.stats[k] for k in self.stats }


    def respondMail(self,msg_id,payload):
        try:
            print('respondMail()')
            d = {
                'responses': [
                    {
                        'msg_id': msg_id,
                        'type': 'response',
                        'payload': payload,
                    },
                ],
            }
            self._addLoginTok(d)
            url = self.config['mail_post_url']
            res = requests.post(url, json = d, timeout=20)
            return res
        except Exception as e:
            print('problem_posting_mail_response',e)
            return None

        

    def getMail(self):
        try:
            print('getMail()')
            d = {}
            self._addLoginTok(d)
            url = self.config['mail_fetch_url'] + '?qstr=' + quote_plus(json.dumps(d))
            res = requests.get(url, timeout = 20)
            return res.json()
        except Exception as e:
            print('mail_fetch_exception',e)
            return [] 

    def ping(self):
        try:
            print('ping()')
            now = datetime.datetime.now(datetime.timezone.utc)
            data = {
                'source_type': self.config['device_type'],
                'date': now.isoformat(),
            }

            self._addLoginTok(data)
            self._addDiagInfo(data)

            res = requests.post(self.config['ping_url'], json = data, timeout=20)
            self.stats['ping_attempts'] += 1
            if self.help.httpOK(res.status_code):
                self.stats['consec_net_errs'] = 0
            else:
                self.stats['consec_net_errs'] += 1
                self.stats['ping_failures'] += 1
            return res
        except Exception as e:
            print(e)
            return None


    def _addLoginTok(self, sdata):

        tok = self.help.b64str2bytes(self.creds['token'])
        srv_salt = self.help.b64str2bytes(self.creds.get('server_salt',''))
        serial = self.config['device_serial']

        combined = tok + srv_salt + serial

        src_tokhash = hashlib.sha512(combined).digest()

        new_salt = self.help.makeRandomBytes(128)

        combined = src_tokhash + new_salt
        h1_dig = hashlib.sha512(combined).digest()

        sdata['identification'] = {
            'node_name': self.creds.get('node_name',''),
            'salt': self.help.bytes2b64str(new_salt),
            'salted_tok': self.help.bytes2b64str(h1_dig),
        }

        dB('tok',tok)
        dB('srv_salt',srv_salt)
        dB('serial',serial)
        dB('combined',combined)
        dB('src_tokhash', src_tokhash)
        dB('new_salt', new_salt)
        dB('h1_dig', h1_dig)


    def push(self, sdata):
        print('uploadData()')
        now = datetime.datetime.now(datetime.timezone.utc)

        data = {
            'sensor_data': sdata,
            'source_type': self.config['device_type'],
            'date': now.isoformat(),
        }

        self._addLoginTok(data)
        self._addDiagInfo(data)

        res = requests.post(self.config['post_url'], json = data, timeout=60)
        self.stats['push_attempts'] += 1
        if self.help.httpOK(res.status_code):
            self.stats['consec_net_errs'] = 0
        else:
            self.stats['consec_net_errs'] += 1
            self.stats['push_failures'] += 1
        return res


    def _addDiagInfo(self, data):
        data['diagnostic'] = {
            'host': {
                'ifaces': self.interfaces,
                'name': self.hostname,
                'uptime': self.help.strTimeDelta(self.help.sysUptime()),
            },
            'service': {
                'stats': self.stats,
                'uptime': self.help.strTimeDelta(self.help.svcUptime()),
            },
        }
    def getParams(self, params = {}):
        self._paramsLocalOverride(params)
        self._paramsRemoteOverride(params)

    def _replkeys(self, dst, src, label = ''):
        for key in src:
            if key not in self.non_override_keys:
                print('[{0}] Override params[{1}] = {2}'.format(label,key,json.dumps(src[key])))
                dst[key] = src[key]

    def _paramsLocalOverride(self,params):
        fn = self.config['params_path']
        try:
            with open(fn,'r') as fh:
                data = json.loads(fh.read())
                self._replkeys(params, data, 'local')
        except Exception as e:
            print('Got exception reading local overrides');
            print(e)


    def _paramsRemoteOverride(self,params):
        print('_paramsRemoteOverride')
        try:
            d = {}
            self._addLoginTok(d)
            url = self.config['params_url'] + '?qstr=' + quote_plus(json.dumps(d))
            res = requests.get(url, timeout=30)
            if res.status_code == 200:
                data = res.json()
                self._replkeys(params, data, 'remote')
            else:
                print('Got error code fetching params from server.')
        except Exception as e:
            print('Got exception fetching params.')
            print(e)


    def _selfProvision(self):
        print('_selfProvision')

        name = self.config.get('device_name',None)
        if name is None:
            name = "d3s_" + self.help.makeRandomString(10)

        provtok = None
        with open(self.config['provisioning_token_path'],'r') as ptfh:
            provtok = json.load(ptfh)

        reqdata = {
            'serial_number': self.config['device_serial'],
            'provtok': provtok,
            'name': name,
        }
        res = requests.post(self.config['url_base'] + '/device/setup/' + name, reqdata)
        print(res)
        if res.status_code == 200:
            resdata = res.json()
            return resdata
        return None


    def _loadCredentials(self):
        try:
            with open(self.config['credentials_path'],'r') as fh:
                creds = json.load(fh)
                return creds
        except Exception as e:
            print('Problem loading credentials')
            print(e)
            try:
                creds = self._selfProvision()
                if creds:
                    with open(self.config['credentials_path'],'w') as fh:
                        fh.write(json.dumps(creds))
                    if False:
                        os.unlink(self.config['provisioning_token_path'])
                    return creds
                else:
                    print('Could not self-provision. Exiting.')
                    raise Exception('self_provisioning_bad_result_or_could_not_store')
            except Exception as f:
                print('Self provisioning failed.')
                raise Exception('self_provisioning_failed')



class _Helpers():
    def __init__(self):
        self.initUptime = self.sysUptime()
    def makeRandomBytes(self, N):
        if no_secrets:
            return bytes(os.urandom(N))
        else:
            return secrets.token_bytes(N)
    def makeRandomString(self, N):
        if no_secrets:
            return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(N))
        else:
            return ''.join(secrets.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(N))
    def bytes2b64str(self, b):
        return b64.b64encode(b).decode('ascii')
    def b64str2bytes(self, s):
        return b64.b64decode(s)

    def myPublicIP(self):
        try:
            return requests.get('https://ipinfo.io').json()['ip']
        except:
            return 'dunno'
    def myInterfaces(self):
        try:
            ifnames = netifaces.interfaces()
            return { ifn: netifaces.ifaddresses(ifn) for ifn in ifnames }
        except Exception as e:
            print('Exception getting network IF info', e)
            return 'dunno'
    def myHost(self):
        host = 'unknown'
        try:
            host = socket.gethostname()
        except:
            pass
        return host
    def httpOK(self,n):
        return n >= 200 and n < 300
    def sysUptime(self):
        ut_seconds = 0
        try:
            with open('/proc/uptime','r') as f:
                ut_seconds = float(f.readline().split()[0])
        except:
            pass
        return ut_seconds
    def strTimeDelta(self,td):
        days = td // 86400
        td -= days * 86400
        hours = td // 3600
        td -= hours * 3600
        minutes = td // 60
        td -= minutes * 60
        seconds = td
        f = [int(x) for x in [days,hours,minutes,seconds]]
        return("{0}d {1}h {2}m {3}s".format(*f))
    def svcUptime(self):
        return self.sysUptime() - self.initUptime
