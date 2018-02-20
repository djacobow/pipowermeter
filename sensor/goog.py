#!/usr/bin/env python3
import os
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
import httplib2


class Googleizer():
    def __init__(self, icfg = {}):
        self.secrets_file = './google_client_secret.json'
        self.cred_dir = '.goog-credentials'
        self.cred_fn = 'power_uploader_sheets.json'
        self.tableRange = 'a1:zz999999'
        self.ua = 'power_upload/0.1'
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive',
        ]
        for kn in icfg:
            setattr(self,kn,icfg[kn])

        try:
            import argparse
            self.flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
            print(self.flags)
        except ImportError:
                self.flags = None
        self.check_creds()
        self.setup_service()




    def check_creds(self):
        home = os.path.expanduser('~');
        cred_dir = os.path.join(home, self.cred_dir)
        if not os.path.exists(cred_dir):
            os.makedirs(cred_dir)
        cred_path = os.path.join(cred_dir, self.cred_fn)
        store = Storage(cred_path)
        creds = store.get()
        if not creds or creds.invalid:
            self.get_creds(store)
        else:
            self.credentials = creds

    def get_creds(self, store):
        flow = client.flow_from_clientsecrets(self.secrets_file,self.scopes)
        flow.user_agent = self.ua
        creds = tools.run_flow(flow, store, self.flags)
        self.credentials = creds
        return self.credentials


    def setup_service(self):
        http = self.credentials.authorize(httplib2.Http())
        self.sheet_svc = discovery.build('sheets','v4',http=http)
        self.drive_svc = discovery.build('drive','v3',http=http)

    def createSheet(self, name, parent = None):
        body = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.spreadsheet',
        }

        if parent is not None:
            body['parents'] = [ parent ]

        request = self.drive_svc.files().create(body=body)
        result = request.execute()
        print(result)
        return result.get('id',None)


        
    def addRows(self,sheet,rows):
        req = {
            'spreadsheetId': sheet,
            'range': self.tableRange,
            'valueInputOption': 'RAW',
            'insertDataOption': 'INSERT_ROWS',
            'includeValuesInResponse': True,
            'body': {
                'majorDimension': 'ROWS',
                'values': rows,

            },
        }

        request = self.sheet_svc.spreadsheets().values().append(**req)
        result = request.execute()
        return result


       



if __name__ == '__main__':
    g = Googleizer()

    ns = g.createSheet('bob1', '11EIJbrb8SA75A_SgIBAV6t8EWD8A1XiB')
    print(ns)
    #@sn = '1SyKJFOPoYrLww4qLWlkRfv_3tJNOE9XJfd5ZOdnhiGA'
    #r = g.addRow(sn, [[1,2,3],['a','b','c']])
    #print(r)


