import streamlit as st
import requests
from requests.structures import CaseInsensitiveDict
import csv
import json
import datetime
import time

# Add the hostname here based on the POD 

#uncomment the right login server 
#loginserver="https://dm-us.informaticacloud.com"
#loginserver="https://dm-em.informaticacloud.com"
#TODO Add a drop down to choose the region and POD details 

#uncomment the right server 
#server="https://na1.dm-us.informaticacloud.com/saas/"
#

#login_url = loginserver+"/saas/public/core/v3/login"

def login(username, password):
    payload = """
    {
        "username": "%s",
        "password": "%s"
    }
    """ % (username, password)

    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/json"
    
    # Send the login request and retrieve the session ID
    response = requests.post(login_url, headers=headers, data=payload)
    if response.status_code != 200:
        raise ValueError("Invalid credentials. Please try again.")
    userInfo = response.json()["userInfo"]
    #st.write(userInfo)
    session_id=userInfo["sessionId"]
    org_id=userInfo["orgId"]
    orgName=userInfo["orgName"]
    st.write("Org Id is :"+org_id)
    return session_id,org_id
    
def logout(session_id):
    logout_url=loginserver+"saas/public/core/v3/logout"
    headers = {"INFA-SESSION-ID": session_id}
    out_response = requests.post(logout_url,headers=headers)
    if out_response.status_code != 200:
        st.write("Log out Failed!");
        st.write(out_response.content)
    else:
        st.write("Logged out successfully")
    

def get_verifiers(session_id):
    objects_url = FRSserver+"saas/public/core/v3/objects?q=type==VERIFIER&limit=20"
    #st.write(objects_url)
    headers = {"INFA-SESSION-ID": session_id}
    # Send the objects request and retrieve the JSON output
    
    response = requests.get(objects_url,headers=headers)
    json_output = response.json()
    verifiers = json_output["objects"]
    
    return verifiers

def get_dependencies(session_id, oid):
    dependecies_url=FRSserver+"saas/public/core/v3/objects/"+oid+"/references?refType=Usedby"
    headers = {"INFA-SESSION-ID": session_id}
    dependencies_response = requests.get(dependecies_url,headers=headers)
    dependencies = dependencies_response.json()["references"]
    #st.write(dependencies)
    return dependencies
    
def get_agentconfigurations(session_id,org_id):
    agent_url=FRSserver+"saas/api/v2/agent"
    headers = {"icSessionId": session_id}
    agents_response=requests.get(agent_url,headers=headers)
    #st.json(agents_response.json())
      
    aid_list=["Agent ID"]
    aname_list=["Agent Name"]
    aconfigs_types=["Config Type"]
    aconfigs_names=["Config Names"]
    aconfig_values=["Config Value"]
    aconfig_changed=["Customized"]
    aconfig_defaults=["Defaults"]
    st.write("Fetching AV related properties for the agents")   
    for agent in agents_response.json():
        aid=agent["id"]
        aname=agent["name"]
        aplat=agent["platform"]
        ahost=agent["agentHost"]
        agid=agent["agentGroupId"]
            
        st.write( aname + "(" + ahost+")")
            
        agentdetails_url=FRSserver+"saas/api/v2/agent/details/"+aid
        headers = {"icSessionId": session_id}
        agentsdetails_response=requests.get(agentdetails_url,headers=headers)
            
        #st.write(agentsdetails_response.json()["id"])
        for configs in  agentsdetails_response.json()["agentEngines"]:
                #st.write(configs["agentEngineConfigs"])
                for config in configs["agentEngineConfigs"]:
                    if(config["type"]=="IDQAD" or config["type"]=="CDQAV"  ):
                        #st.write(config)
                        aid_list.append(aid)
                        aname_list.append(aname)
                        aconfigs_types.append(config["type"])
                        aconfigs_names.append(config["name"])
                        aconfig_values.append(config["value"])
                        aconfig_changed.append(config["customized"])
                        aconfig_defaults.append(config["defaultValue"])
                        
    arows=list(zip(aid_list,aname_list,aconfigs_types,aconfigs_names,aconfig_values,aconfig_changed,aconfig_defaults  ))
    filename=org_id+"cons_Agent_properties.csv"
    with open(filename, "w", newline="") as csvfile:
            # Create a CSV writer object
        writer = csv.writer(csvfile)

            # Write each row to the CSV file
        for row in arows:
                writer.writerow(row)
    create_download_link(filename)
    

def export_dependecies_csv(verifiers,org_id):
    
    vid = ["Verifier ID"]
    vname = ["Verifier Name"]
    vupdatelist=["Verifier Last updated time"]
    did = ["Dependent Object id"]
    dname = ["Dependent Object name"]
    dtype = ["Dependent Object Type"]
    dupdatedlist=["Dependent Last updated time"]
    for verifier in verifiers:
        oid = verifier["id"]
        name = verifier["path"]
        vupdated=verifier["updateTime"]
        dependencies = get_dependencies(session_id, oid)
        count = len(dependencies)
        for iter in range(0, count):
            vid.append(oid)
            vname.append(name)
            vupdatelist.append(vupdated)
            did.append(dependencies[iter]["id"])
            dname.append(dependencies[iter]["path"])
            dtype.append(dependencies[iter]["documentType"])
            dupdatedlist.append(dependencies[iter]["lastUpdatedTime"])
            
    rows=list(zip(vid,vname,vupdatelist,did,dname,dtype,dupdatedlist))
    st.write("Completed Fetching from server. Saving to CSV file ..")
    filename=org_id+"_Verifier_dependencies.csv"
    with open(filename, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        for row in rows:
            writer.writerow(row)
    
    create_download_link(org_id+"_Verifier_dependencies.csv")
    return did
    
def trigger_exportJob(session_id,did):
    #st.write(did); 
    jsonlist=[]
    objcount=len(did)
    
    
    for i in range(1,objcount):
        jsonlist.append({"id":did[i],"includeDependencies": "true" })
   # st.write(json.dumps(jsonlist))   
    now = datetime.datetime.now()
    datetime_str = now.strftime("%Y%m%d_%H%M%S")
    exportjobname="Preupgrade_Export"+datetime_str
    jsonbody={"name": exportjobname, "objects": jsonlist}
    st.write(json.dumps(jsonbody))
    export_url = FRSserver+"saas/public/core/v3/export"
    headers = {"INFA-SESSION-ID": session_id,"Content-Type":"application/json"}
    export_response=requests.post(export_url, data=json.dumps(jsonbody),headers=headers)
    if export_response.status_code == 200:
        st.write("Export request  successful!Export job will start soon")
        st.write(export_response.json())
        return export_response.json()["id"]
    else:
        st.write("Export request failed with status code:", export_response.status_code)
        st.write(export_response.content)
        return -1



def get_Export_Download(session_id,jobid,org_id):
    
    download_url = FRSserver+"saas/public/core/v3/export/"+jobid+"/package"
    headers = {"INFA-SESSION-ID": session_id,"accept":"application/zip"}
    download_response=requests.get(download_url, headers=headers)
    #st.write(download_response)
    if download_response.status_code == 200:
    # Get the file content from the response
        file_content = download_response.content

    # Save the file content to a local file
        filename=org_id+"_"+jobid+".zip"
        with open(filename, "wb") as file:
            file.write(file_content)
        create_download_link(filename)
    else:
        st.write("Download Failed.Please check the portal  for job status and download it manually.The job id is "+jobid)
        

    
       
def create_download_link(file_name):
    with open(file_name, "rb") as f:
        file_contents = f.read()
        st.download_button(
            label="Download " + file_name,
            data=file_contents,
            file_name=file_name,
            mime="application/octet-stream"
        )

        
st.header("Informatica Cloud Login")


st.header("Informatica AV Upgrade Information Portal Login(GCS)")
podoption = st.selectbox(
     'select the pod region ',
    (('emw1.dm-em','na1.dm-us','na2.dm-us','usw3.dm-us','use4.dm-us','usw5.dm-us','use6.dm-us','apse1.dm-ap','nac1.dm-na','usw1.dm1-us','usw3.dm1-us','emc1.dm1-em','apse1.dm1-apse','apne1.dm1-ap','na1.iics-icinq1','uk1.dm-uk','apauc1.dm1-apau','usw1.dm2-us','apne2.dm-apne','emse1.dm1-emse')))

serversuffix=".informaticacloud.com/"
serverprefix="https://"
FRSserver=serverprefix+podoption+serversuffix
st.write("FRS server for selected region is :" +FRSserver) 
end_char = "."
substring = FRSserver[:FRSserver.index(end_char)+1]
loginserverx=FRSserver
loginserver=loginserverx.replace(substring, "https://")
st.write("Login server "+loginserver)


login_url = loginserver+"saas/public/core/v3/login"

username = st.text_input("Username")
password = st.text_input("Password", type="password")
submit = st.button("Login")



if submit:

    session_id,org_id=login(username,password)
    #st.write(session_id)
    verifiers=get_verifiers(session_id)
   # st.write(verifiers)
    didlist=export_dependecies_csv(verifiers,org_id)
    
    get_agentconfigurations(session_id,org_id)
    
    jobid=trigger_exportJob(session_id,didlist)
    if jobid != -1 :
        st.write("Please wait, a download request will be attempted after waiting for 30 seconds")
        time.sleep(10)
        st.write("Attempting Download") 
        download_status=get_Export_Download(session_id,jobid,org_id)
        
        
    logout(session_id)
    
    
    
    