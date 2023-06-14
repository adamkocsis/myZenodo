import json
import requests

from .utility import hashing

LINK = None
TOKEN = None

def configure(sandbox=True, tokens = ''):
    global LINK
    global TOKEN
    
    # open the local JSON file that has my tokens
    with open(tokens) as f:
        dict_tokens = json.load(f)
    
    if sandbox:
        LINK = 'https://sandbox.zenodo.org' 
        TOKEN = dict_tokens['sandbox'] 
    else:
        LINK = 'https://zenodo.org' 
        TOKEN = dict_tokens['real'] 


def show():
    print(LINK)


def add_file(depid, paths):
    # define the access token from module-variable
    params = {'access_token': TOKEN}
    
    # get the bucket url for this upload
    # first get a request for this depid
    req = requests.get(LINK + '/api/deposit/depositions/' + str(depid), params = params)
    
    # proper? 
    if req.status_code != 200:
        print(req.json())
        raise(RuntimeError("Wrong status code during query."))
    
    # now get the bucket URL out of this request
    bucket = req.json()["links"]["bucket"]
    
    # get the filenames
    hashes={}
    for path in paths:
        splits = path.split("/")
        filename = splits[len(splits)-1]
        
        # calculate md5 of file
        orig=hashing(path) 
        
        # save
        hashes[filename] = orig
        # and now put it online
        with open(path, "rb") as fp:
            r = requests.put("%s/%s" % (bucket, filename), data=fp, params=params)
            
    # after the upload, check whether this is correct
    files=list_filedata(depid)
    
    # go through all uploaded files
    for md5 in hashes:
        # the online hash
        online_hash='missing'
        
        # get this from the request
        for online in files:
            # the name of the current online file
            current_name=online['filename']
            # matches
            if current_name==md5:
                online_hash=online['checksum']
                
        # this should not be the starting
        if online_hash=='missing':
            raise(RuntimeError("The file '" + md5 + "' was uploaded but it is not found online." ))
                
        # now check whether it is the same 
        if online_hash!=hashes[md5]:
            raise(RuntimeError("The file '" + md5 + "' was uploaded but checksum failed." ))
        
    print("Successfully uploaded " + str(len(hashes)) + " files.")
    return(hashes)
        
        

# returns the request of the upload
def discard(depid):
    params = {'access_token': TOKEN}
    delete = requests.delete(LINK + '/api/deposit/depositions/' + str(depid) , params=params)
    
    # either return the request or just the depo ID
    if delete.status_code != 204:
        print(delete.json())
        raise(RuntimeError("Wrong status code during query."))
    
    print("Discarded Zenodo deposition id. " + str(depid)+ ".")
        


def list_filedata(depid):
    params = {'access_token': TOKEN}
    req = requests.get(LINK + '/api/deposit/depositions/' + str(depid) + '/files', params = params)
    return(req.json())
    

def list_files(depid):
    params = {'access_token': TOKEN}
    req = requests.get(LINK + '/api/deposit/depositions/' + str(depid) + '/files', params = params)
    all=req.json()
    all_files=[]
    for entry in all:
        all_files.append(entry['filename'])
    return(all_files)



def new():
    # define the headers
    headers = {"Content-Type": "application/json"}
    
    # define the access token from module-variable
    params = {'access_token': TOKEN}
    
    # the upload request
    upload = requests.post(LINK + '/api/deposit/depositions', params=params, json={}, headers=headers)
    
    # either return the request or just the depo ID
    if upload.status_code != 201:
        print(upload.json())
        raise(RuntimeError("Wrong status code during query."))
    
    # get the ID of this
    # return the json format
    depid =upload.json()['id'] 
    print("Created new Zenodo deposition id. " + str(depid)+ ".")
    
    # return only the ID
    return depid 




def new_version(depid):
    # define the headers
    headers = {"Content-Type": "application/json"}
    
    # define the access token from module-variable
    params = {'access_token': TOKEN}
     
    # request for new version
    newver = requests.post(LINK + '/api/deposit/depositions/' + str(depid) +'/actions/newversion', params=params)
    
    # check he status code
    if newver.status_code != 201:
        print(newver.json())
        raise(RuntimeError("Wrong status code during query."))
    
    # mine out the new deposition ID
    latest = newver.json()['links']['latest_draft']
    new_depid = latest.split("/")[len(latest.split("/"))-1] 
    
    print("Created new version of "+ str(depid)+", Zenodo deposition id. " + str(new_depid)+ ".")
    # return the id of the new deposition
    return new_depid

def publish(depid):
    # define the access token from module-variable
    params = {'access_token': TOKEN}
    
    # try to publish this
    published = requests.post(LINK + '/api/deposit/depositions/%s/actions/publish' % depid, params=params)
    
    print("Successfully published " + str(depid))
    # get the bucket url for this upload

    # frequently gets FF-ed up
    doiTry=True
    while doiTry:
        # first get a request for this depid
        req = requests.get(LINK + '/api/deposit/depositions/' + str(depid), params = params)
        # get the download links for this 
        try:
            doi=req.json()['doi']
            doiTry=False
        except: 
            print("Failed json doi access, trying again. ")
    
    return(doi)



def remove_files(depid, files=None):
    params = {'access_token': TOKEN}
    # download information of the online files
    online=list_filedata(depid)
    
    # recursive case - remove everything
    if files is None:
        remove_files(depid, files=list_files(depid))
    
    # base case
    else:
        # go through the filenames and do the job
        deleted=0
        for file in files:
            found=False
            # look through all the online files
            for on in online:
                # if this is the current file
                if on['filename']==file:
                    # remove
                    req = requests.delete(on['links']['self'], params = params)
                    found=True
                    deleted=deleted+1
            if not found:
                print('The file was not online.')
                
        print("Successfully deleted " + str(deleted) + " files.")


def update_meta(depid, data):
    # check the contents of data - these are required fields!
    if 'title' not in data.keys():
        raise(RuntimeError("The Zenodo metadata must have a 'title'. "))
    if 'upload_type' not in data.keys():
        raise(RuntimeError("The Zenodo metadata must have an 'upload_type'. "))
    if 'description' not in data.keys():
        raise(RuntimeError("The Zenodo metadata must have an 'description'. "))
    
    # add the necessary wrapper
    all_data = {
        'metadata': data
    }
    
    # define the headers
    headers = {"Content-Type": "application/json"}
    
    # define the access token from module-variable
    params = {'access_token': TOKEN}
    
    # added details
    added = requests.put(LINK + '/api/deposit/depositions/%s' % depid, params=params, data=json.dumps(all_data), headers=headers)
    
    # proper? 
    if added.status_code != 200:
        print(added.json())
        raise(RuntimeError("Wrong status code during query."))
    
    print("Updated metadata of Zenodo deposition id. " + str(depid)+ ".")

def get_links(depid):
    # download the files that are available
    files=list_files(depid)
    links={}
    for file in files:
       links[file]=LINK +  "/record/" + str(depid) + "/files/" + file + "?download=1"
    return(links)
        
    
