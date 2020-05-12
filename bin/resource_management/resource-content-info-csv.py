#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import urllib
import sys
from sys import stderr, stdout, argv
import requests
from datetime import datetime
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from multiprocessing import Process
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


# In[2]:


def run_cpu_tasks_in_parallel(tasks):
    """
    Manages processes
    tasks - list of methods to be run
    """
    running_tasks = [Process(target=task) for task in tasks]
    for running_task in running_tasks:
        running_task.start()
    for running_task in running_tasks:
        running_task.join()
        
def internet_on():
    """
    tests internet connection by pinging google
    """
    try:
        urllib.request.urlopen('http://216.58.192.142', timeout=1)
        return True
    except Exception as err: 
        return False
    
def main(filename,processes=4):
    """
    Scan url's of resources from dataset metadata obtained from https://open.canada.ca/data/en
    CKAN API - ckanapi dump datasets --all -O datasets.jsonl.gz -z -p 4 -r http://localhost
    
    filename - destination of jsonl/jl file 
    processes - default processes=4. Number of batches and processes to run. Will export 1 file per process.
    
    Exports resource file information found in metadata as CSV
    """
    try:
        df=pd.read_json(filename,lines=True)
    except:
        print('Error: .jsonl/.jl file expected')
        return False
    file_length = len(df)
    batchsize=round(file_length/processes)
    tasks=[]
    for i in range(processes):
        lower = i*batchsize
        upper = (i+1)*batchsize
        if(i==processes-1):
            upper=file_length
        tasks.append(get_url_info(lower,upper,i,df))
    run_cpu_tasks_in_parallel(tasks)
    


# In[5]:


def get_url_info(lower,upper,batch_number,df):
    """
    Scan url's of resources of current batch from dataset metadata obtained from https://open.canada.ca/data/en
    
    lower - starting index of batch
    upper - final index of batch
    batch_number - current batch number
    df - copy of metadata dataframe
    
    exports CSV of resource content length in kb from current batch - 'file_info_batch{0}.csv'.format(batch_number)
    """
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M")
    file_info=[]
    for i in range(lower,upper):
        uuid = df["id"][i]
        title = df["title"][i]
        org = df["organization"][i].get("title")
        dataset_url = "https://open.canada.ca/data/en/dataset/"+uuid
        resources = df["resources"][i]
        for z in range(len(resources)):
            if("url" in resources[z]):
                res_name=resources[z].get("name")
                res_url=resources[z].get("url")
                res_fmt = resources[z].get("format").lower()
                content_length = None
                c2=None
                try:
                    ##try requests first as it is faster than urllib
                    if('http://' in res_url or 'https://' in res_url):
                        resHead = requests.head(res_url,verify=False) 
                        headers =resHead.headers
                        content_type=(((headers.get("Content-type").split(';'))[0]).split('/'))[1]
                        content_length=headers.get("Content-length")
                    if('ftp://' in res_url or content_length is None):
                        c = urllib.request.urlopen(res_url)
                        c2=(((c.info().get("Content-Type").split(';'))[0]).split('/'))[1]
                        content_length=c.info().get("Content-Length")
                        c.close()
                    if(c2 is None):
                        file_info.append([uuid,title,org,dataset_url,res_name,res_url,res_fmt,
                                          content_type,content_length,dt_string])
                    else:
                        file_info.append([uuid,title,org,dataset_url,res_name,res_url,res_fmt,
                                          c2,content_length,dt_string])
                except Exception as e:
                    s=str(e)
                    if(not(internet_on())):
                        i-=1
                    while(not(internet_on())):
                        print(' LOST INTERNET CONNECTION at index: ',i," batch#: ",(i+1)%100)
                    continue;

        percent = float(i) / upper
        arrow = '-' * int(round(percent * 20)-1) + '>'
        spaces = ' ' * (20 - len(arrow))
        if((i+1)%100 ==0):
            #export every 100 entries
            export_df = pd.DataFrame(file_info, columns = ['uuid','title','organization','dataset_url','resource_name','resource_url',
                                                   'resource_format','download_format','content_length_kb','date_checked'])
            export_df.to_csv('file_info_batch{0}.csv'.format(batch_number), index=False)

        sys.stdout.write("\rBatch# {4} Percent: [{0}] {1}% -- {2} of {3} checked".format
                         (arrow + spaces, int(round(percent * 100)),i,upper,batch_number))
        sys.stdout.flush()

    #Export at end
    export_df = pd.DataFrame(file_info, columns = ['uuid','title','organization','dataset_url','resource_name','resource_url',
                                                   'resource_format','download_format','content_length_kb','date_checked'])
    export_df.to_csv('file_info_batch{0}.csv'.format(batch_number), index=False)
    


# In[6]:


filename,processes = sys.argv[1], sys.argv[2]
main(filename,processes)


# In[ ]:




