#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import urllib
import sys
from sys import stderr, stdout, argv
from multiprocessing import Process


# In[ ]:


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
        
def main(filename,processes=4):
    """
    Scan url's of resources from dataset metadata obtained from https://open.canada.ca/data/en
    CKAN API - ckanapi dump datasets --all -O datasets.jsonl.gz -z -p 4 -r http://localhost
    
    filename - destination of jsonl/jl file 
    processes - default processes=4. Number of batches and processes to run. Will export 1 file per process.
    
    Exports broken links found in metadata
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
        tasks.append(verify_url(lower,upper,i,df))
    run_cpu_tasks_in_parallel(tasks)


# In[ ]:


def verify_url (lower,upper,batch_number,df):
    """
    Scan url's of resources of current batch from dataset metadata obtained from https://open.canada.ca/data/en
    
    lower - starting index of batch
    upper - final index of batch
    batch_number - current batch number
    df - copy of metadata dataframe
    
    exports CSV of broken links from current batch - 'od-broken-links_batch{0}.csv'.format(batch_number)
    """
    broken_links=[]
    for i in range(lower,upper):
        resources = df["resources"][i]
        error='no-code'
        for z in range(len(resources)):
            flag=0
            if("url" in resources[z]):
                name=resources[z].get("name")
                url=resources[z].get("url")
                try:
                    c = urllib.request.urlopen(url)
                    if(c.getcode() is None or c.getcode()<400):
                        continue;
                    else:
                        error=c.getcode();
                        flag=1;
                except Exception as e:
                    if (c.getcode() is not None or c.getcode()>=400):
                        s=str(e)
                        error=s
                        flag=1
            if(flag==1):
                uuid = df["id"][i]
                title = df["title"][i]
                org = df["organization"][i].get("title")
                date = df["portal_release_date"][i]
                dataset_url = "https://open.canada.ca/data/en/dataset/"+uuid
                broken_links.append([uuid,title,org,date,dataset_url,name, url,error])
                
        percent = float(i) / upper
        arrow = '-' * int(round(percent * 20)-1) + '>'
        spaces = ' ' * (20 - len(arrow))

        sys.stdout.write("\rBatch# {4} Percent: [{0}] {1}% -- {2} of {3} checked".format
                         (arrow + spaces, int(round(percent * 100)),i,upper,batch_number))
        sys.stdout.flush()

    export_df = pd.DataFrame(broken_links, columns = ['uuid', 'title','organization','portal_release_date','dataset_url',
                                                      'resource_name','broken_link','error'])
    export_df.to_csv('od-broken-links_batch{0}.csv'.format(batch_number), index=False)


# In[ ]:


filename,processes = sys.argv[1], sys.argv[2]
main(filename,processes)


# In[ ]:





# In[ ]:




