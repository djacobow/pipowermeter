import subprocess
import datetime
import os

def nowISO():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

class Backgrounder(object):

    def __init__(self, *kwargs):
        self.c = {
            'rundir': './backgrounder/',
            'scriptname': 'script.sh',
        }
        for a in kwargs:
            self.c[a] = kwargs[a]

        self.activities = {}


    def _activitySetup(self, msg):

        setupres = {
            'status': 'ready',
        }

        msg_id = msg.get('msg_id', None)
        if msg_id is None:
            setupres['status'] = 'missing_msg_id'
            return setupres
        else:
            setupres['msg_id'] = msg_id

        script_text = msg.get('payload',None)
        if script_text is None:
            setupres['status'] = 'missing_payload'
            return setupres

        msg_type = msg.get('type',None)
        if msg_type != 'shell_script':
            setupres['status'] = 'not_a_script'
            return setupres

        run_dir = self.c['rundir'] + msg_id
        script_path = run_dir + '/' + self.c['scriptname']
        setupres['run_dir'] = run_dir
        setupres['script_path'] = script_path
        setupres['setup_time'] = nowISO()
        if not os.path.isdir(run_dir):
            try:
                os.makedirs(run_dir)
            except Exception as e:
                setupres['status'] = 'failed_folder_create'
                return setupres;

        try:
            with open(script_path,'w') as ofh:
                ofh.write(script_text)
        except Exception as e:
            setupres['status'] = 'failed_script_create'
            return setupres

        try:
            os.chmod(script_path, 0o766)
        except Exception as e:
            setupres['status'] = 'failed_make_executable'
            return setupres
        
        return setupres



    def startNew(self, msg):


        msg_id = msg.get('msg_id',None)
        if msg_id:
            setupres = self._activitySetup(msg)

            self.activities[msg_id] = {
                'setup': setupres,
            }

            if setupres['status'] == 'ready':
                p = subprocess.Popen(setupres['script_path'], shell=True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
                self.activities[msg_id]['handle'] = p
                self.activities[msg_id]['status'] = 'started' 
                self.activities[msg_id]['start_time'] = nowISO()
            else:
                pass


    def _extractResults(self, handle):
        code = handle.returncode
        stdout, stderr = handle.communicate()
        stdout = stdout.decode('utf-8').splitlines()
        stderr = stderr.decode('utf-8').splitlines()
        return { 'code': code, 'stdout': stdout, 'stderr': stderr, }

    def __del__(self):
        msg_ids = list(self.activities.keys())
        for msg_id in msg_ids:
            handle = self.activities[msg_id].get('handle',None)
            if handle:
                handle.kill()


    def checkResults(self):
        results = {}
        rcount = 0
        msg_ids = list(self.activities.keys())
        for msg_id in msg_ids:
            if self.activities[msg_id]['setup']['status'] == 'ready':
                activity = self.activities[msg_id]
                done = activity['handle'].poll()
                if (done is not None):
                    rcount += 1
                    activity['status'] = 'complete' 
                    results[msg_id] = {
                        'stop_time': nowISO(),
                        'setup': self.activities[msg_id]['setup'],
                        'result': self._extractResults(activity['handle'])
                    }
                    del self.activities[msg_id]
                else:
                    pass
            else:
                rcount += 1
                results[msg_id] = {
                    'setup': self.activities[msg_id]['setup'],
                }
                del self.activities[msg_id]
        # print('rcount',rcount,'results',results)
        return rcount, results



