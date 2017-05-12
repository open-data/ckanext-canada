import sys
import subprocess
import requests

'''
Usage: python pd_ati_monitor.py usr1@reg_host usr2@portal_host slack_url
'''

def sendSlack2(text, url):
    payload = {"text":text}
    count = 5
    while count >0:
        count -= 1
        r = requests.post(url, json=payload)
        if r.status_code == 200:
            break
    

def getCSVUpload(usrAtHost):
    
    cmd = 'ssh '+usrAtHost+' grep download /home/odatsrv/run_log/upload_ati_csv_from_datastore_tables.log | wc'
    cmd = cmd.split(' ')
    result = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]
    return int(result.split()[0])


def getPDUpdate(usrAtHost):
    cmd = 'ssh '+usrAtHost+' grep Cleared /home/odatsrv/run_log/rebuild_pd_solr_from_uploaded_csv.log | wc'
    cmd = cmd.split(' ')
    # Python3
    #result = subprocess.run(cmd, stdout=subprocess.PIPE)
    #result.stdout.decode('utf-8')
    result = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]
    return int(result.split()[0])


def main():
    usrAtReg = sys.argv[1]
    usrAtPortal = sys.argv[2]
    slackUrl = sys.argv[3]
    if getCSVUpload(usrAtReg) ==15:
        text = ' csv ok,'
    else:
        text = ' csv bad,'

    if getPDUpdate(usrAtPortal) ==9:
        text += ' solr ok.'
    else:
        text += ' solr bad.'

    count = 5
    while count > 0:
        count -= 1
        try:
            sendSlack2(text, slackUrl)
            break
        except:
            pass

if __name__=='__main__':
    main()
