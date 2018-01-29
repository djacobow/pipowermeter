import requests
import time
import datetime

# This is like a poor man's NTP. Very simple time synchronizer
# that is adequate for some purposes. On LBLnet I can get servers
# synchronized with to sub-millisecond accurary.

# As an alternative to NTP, NTPd should be disabled if you're using
# this module.

class Synchronizer():

    def __init__(self, **kwargs):
        self.c = {
            'time_url': 'https://skunkworks.lbl.gov/radmon/device/time',
            'attempts': 20,
            'min_successes': 5,
            'timeout': 5,
        }

        for a in kwargs:
            self.c[a] = kwargs[a]

        self.last_delta = None


    def _getOneDelta(self):
        try:
            start = time.time()
            res = requests.head(self.c['time_url'], timeout= self.c['timeout'])
            stop = time.time()
            if res.status_code == 200:
                remote_ts = float(res.headers['server_time_epoch_ms']) / 1000
                rtt = stop - start
                local_remote_delta = remote_ts + (rtt / 2) - stop
                return {
                    'result': 'success',
                    'local': {
                        'start': start,
                        'stop': stop,
                        'rtt': rtt,
                    },
                    'remote': {
                        'ts': remote_ts,
                    },
                    'local_remote_delta': local_remote_delta
                }
            else:
                return { 'result': 'badstatus_' + res.status_code}


        except requests.exceptions.Timeout:
            return { 'result': 'timeout' }
        except Exception as e:
            return { 'result': repr(e) }



    def getDelta(self):
        self.last_delta = None

        attempts = []
        for i in range(self.c['attempts']):
            r = self._getOneDelta()
            if r['result'] == 'success':
                attempts.append(r)
            else:
                print(r)

        if len(attempts) < self.c['min_successes']:
            return None


        # get the "middle" / "median" delta value. If the list length
        # is even, get the value adjacent to the median
        sorted_attempts = sorted(attempts, key=lambda x: x['local_remote_delta'])
        middle = sorted_attempts[len(sorted_attempts)//2]

        self.last_delta = middle['local_remote_delta']
        return self.last_delta
        

    def adjClock(self, delta = None):
        if delta is None:
            delta = self.last_delta
        if delta is None:
            print('No delta provided or stored, so time not set')
            return None

        old_sys_epoch = time.time()
        new_sys_epoch = old_sys_epoch + delta

        old_t = datetime.datetime.fromtimestamp(old_sys_epoch)
        new_t = datetime.datetime.fromtimestamp(new_sys_epoch)

        print("Adjustment delta: {0}".format(delta))
        print("Old sys time: {0}, ts: {1}".format(str(old_t),old_sys_epoch))
        print("New sys time: {0}, ts: {1}".format(str(new_t),new_sys_epoch))

        try:
            time.clock_settime(time.CLOCK_REALTIME, new_sys_epoch)
            print('System clock set.')
            return new_t
        except Exception as e:
            print('Could not set system clock, probably a permissions thing.')
            return None
