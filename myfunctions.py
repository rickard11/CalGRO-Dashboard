# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""


import requests
import json
import pandas as pd
import datetime as dt
import pytz
from dateutil import tz
from dateutil.parser import parse
from getpass import getpass
import concurrent.futures

'''
Dendra API Query

author: Collin Bode
email: collin@berkeley.edu

Purpose: 
Simplifies pulling data from the https://dendra.science time-series data management system.
Dendra API requires paging of records in sets of 2,016.  This library performs
that function automatically. 

Functions are grouped into four categories:

Helper functions
    time_utc(str_time="")
    time_format(dt_time=dt.datetime.now(), time_type='local') # other option for time_type='utc'
    authenticate(email)

List: returns a simple JSON list of available objects
    get_organization_id(orgslug)
    list_organizations(orgslug='all')
    list_stations(orgslug='all',query_add='none')
    list_datastreams_by_station_id(station_id,query_add = '')
    list_datastreams_by_query(query_add = '',station_id = '')
    list_datastreams_by_medium_variable(medium = '',variable = '',aggregate = '', station_id = '', orgslug = '', query_add = '')
    list_datastreams_by_measurement(measurement = '',aggregate = '', station_id = [], orgslug = '', query_add = '')

Get_Meta: returns the full metadata object
    get_meta_organization(orgslug='',orgid='')
    get_meta_station_by_id(station_id,query_add = '')
    get_meta_datastream_by_id(datastream_id,query_add = '')
    get_meta_annotation(annotation_id,query_add = '')
    get_datastream_by_id(datastream_id,query_add = '') 
    get_datastream_id_from_dsid(dsid,orgslug='all',station_id = '')
    
Get_Datapoints: returns timestamp,datavalue pairs
    get_datapoints(datastream_id,begins_at,ends_before=time_format(),time_type='local',name='default')
    get_datapoints_from_id_list(datastream_id_list,begins_at,ends_before=time_format(),time_type='local')
    get_datapoints_from_station_id(station_id,begins_at,ends_before=time_format(),time_type='local')

NOTE: the 'get_datapoints' function, which is the primary reason for this library is quite slow. It will
be replaced in the next version when we have min.io set up on the server to handle very large requests.

Parameters:
    query: a JSON object with the tags, organization, stations, and start/end times
    endpoint: what API endpoint to query. 'datapoints/lookup' (default), 'station','datastream','datapoint', 'annotation'
    interval: datalogger minutes between records, integer. Organizations generally have a default: 5 = ERCZO, 10 = UCNRS, 15 = USGS

References:
code repository:  https://github.com/DendraScience
API documentation: https://dendrascience.github.io/dendra-json-schema
'''

import requests
import json
import pandas as pd
import datetime as dt
import pytz
from dateutil import tz
from dateutil.parser import parse
from getpass import getpass
import concurrent.futures


# Params
url = 'https://api.edge.dendra.science/v2/'  # version 1 (/v1/) of the API has been deprecated
headers = {"Content-Type":"application/json"}



###########################################################
# Time Helper Functions & Authentication
# These apply standardized formating and UTC conversion
#
def time_utc(str_time=""):
    if(str_time == ""):
        dt_time = dt.datetime.now(pytz.utc)
    else:
        dt_time = parse(str_time)
        if(dt_time.tzinfo != pytz.utc):
            dt_time = dt_time.astimezone(pytz.utc)
    return dt_time

def time_format(dt_time=dt.datetime.now(), time_type='local'):
    if(time_type == 'utc'): 
        str_time = dt.datetime.strftime(dt_time, "%Y-%m-%dT%H:%M:%SZ") # "%Y-%m-%dT%H:%M:%S.%f"
    else:
        str_time = dt.datetime.strftime(dt_time, "%Y-%m-%dT%H:%M:%S") # "%Y-%m-%dT%H:%M:%S.%f"
    return str_time

# Authentication is not required for public datasets. Only for restricted datasets. 
def authenticate(email):
    headers['Authorization'] = token
    


###########################################################
# List Functions help find what you are looking for, does not retreive full metadata
# Returns id, name,id pairs, or an array of ids

def get_organization_id(orgslug):
    # orgslug: the short name for an organization. can be found in the url on the dendra.science site.
    # examples: 'erczo','ucnrs','chi','ucanr','tnc','pepperwood', 'cdfw' (may change in future)
    query = {
        '$select[_id]':1,
        'slug': orgslug
    }   
    r = requests.get(url + 'organizations', headers=headers, params=query)
    assert r.status_code == 200
    rjson = r.json()
    return rjson['data'][0]['_id']    

def list_organizations(orgslug='all'):
    """ options: 'erczo','ucnrs','chi','tnc','ucanr','pepperwood' """
    query = {
        '$sort[name]': 1,
        '$select[name]':1,
        '$select[slug]':1
    }
    if(orgslug != 'all'):
        query['slug'] = orgslug
    
    r = requests.get(url + 'organizations', headers=headers, params=query)
    assert r.status_code == 200
    rjson = r.json()
    return rjson['data']    

def list_stations(orgslug='all',query_add='none'):
    """
    orgslug examples: 'erczo','ucnrs','chi'
    NOTE: can either do all orgs or one org. No option to list some,
          unless you custom add to the query."""
    query = {
        '$sort[name]': 1,
        '$select[name]': 1,
        '$select[slug]': 1,
        '$limit': 2016
    }

    # Narrow query to one organization
    if(orgslug != 'all'):
        org_list = list_organizations(orgslug)
        if(len(org_list) == 0): 
            return 'ERROR: no organizations found with that acronym.'
        orgid = org_list[0]['_id'] 
        query['organization_id'] = orgid

    # Modify query adding custom elements
    if(query_add != 'none'):
        for element in query_add:
            query[element] = query_add[element]

    # Request JSON from Dendra         
    r = requests.get(url + 'stations', headers=headers, params=query)
    assert r.status_code == 200
    rjson = r.json()
    return rjson['data']

def list_datastreams_by_station_id(station_id,query_add = ''):
    query = {
        '$sort[name]': 1,
        '$select[name]': 1,
        'station_id': station_id,
        '$limit': 2016
    }
    if(query_add != ''):
        query.update(query_add)    

    # Request JSON from Dendra         
    r = requests.get(url + 'datastreams', headers=headers, params=query)
    assert r.status_code == 200
    rjson = r.json()
    return rjson['data']

def list_datastreams_by_query(query_add = '',station_id = ''):
    query = {
        '$sort[name]': 1,
        '$select[name]': 1,
        '$limit': 2016
    }
    if(query_add != ''):
        query.update(query_add)    
    if(station_id != ''):
        query.update({'station_id': station_id})
        
    # Request JSON from Dendra         
    r = requests.get(url + 'datastreams', headers=headers, params=query)
    assert r.status_code == 200
    rjson = r.json()
    return rjson['data']
    
def list_datastreams_by_medium_variable(medium = '',variable = '',aggregate = '', station_id = '', orgslug = '', query_add = ''):
    # parameters: 
    # medium: Air, Water, Soil, etc 
    # variable: Temperature, Moisture, Radiation, etc
    # aggregate: Minimum, Average, Maximum, Cumulative
    # station_id: MongoID
    # orgslug: shortname (currently erczo, ucnrs, chi, ucanr, tnc, pepperwood)
    # query_add: JSON query please see documentation https://dendrascience.github.io/dendra-json-schema/
    query = {
        '$sort[name]': 1,
        '$select[name]': 1,
        '$limit': 2016
    }
    if(medium != ''):
        query.update({'terms_info.class_tags[$all][0]':"ds_Medium_"+medium})
    if(variable != ''):
        query.update({'terms_info.class_tags[$all][1]':"ds_Variable_"+variable})
    if(aggregate != ''):
        query.update({'terms_info.class_tags[$all][2]':"ds_Aggregate_"+aggregate})    
    if(station_id != ''):
        query.update({'station_id': station_id})
    if(orgslug != ''):
        orgid = get_organization_id(orgslug)
        query.update({'organization_id': orgid})
    if(query_add != ''):
        query.update(query_add)
        
    # Request JSON from Dendra         
    r = requests.get(url + 'datastreams', headers=headers, params=query)
    assert r.status_code == 200
    rjson = r.json()
    
    return rjson['data']

def list_datastreams_by_measurement(measurement = '',aggregate = '', station_id = [], orgslug = '', query_add = ''):
    # parameters: measurements and aggregates are spelled out and capitalized
    # measurement: see dendra.science for list. No spaces. (AirTemperature, VolumetricWaterContent, RainfallCumulative, etc.
    # aggregate: Minimum, Average, Maximum, Cumulative
    # station_id: MongoID
    # orgslug: shortname (currently erczo, ucnrs, chi, ucanr, tnc, pepperwood)
    # query_add: JSON query please see documentation https://dendrascience.github.io/dendra-json-schema/
    query = {
        '$sort[name]': 1,
        '$select[name]': 1,
        '$limit': 2016
    }
    if(measurement != ''):
        query.update({'terms_info.class_tags[$all][0]':"dq_Measurement_"+measurement})
    if(aggregate != ''):
        query.update({'terms_info.class_tags[$all][2]':"ds_Aggregate_"+aggregate})    
    if(station_id != []):
        query.update({'station_id': station_id})
    if(orgslug != ''):
        orgid = get_organization_id(orgslug)
        query.update({'organization_id': orgid})
    if(query_add != ''):
        query.update(query_add)
        
    # Request JSON from Dendra         
    r = requests.get(url + 'datastreams', headers=headers, params=query)
    assert r.status_code == 200
    rjson = r.json()
    return rjson['data']



###########################################################
# Get Metadata Functions
# Returns full metadata JSON object

def get_meta_organization(orgslug='',orgid=''):
    if(orgslug != '' and orgid == ''):
        orgid = get_organization_id(orgslug)
    if(orgid != ''):
        query = { '_id': orgid }
        r = requests.get(url + 'organizations', headers=headers, params=query)
        assert r.status_code == 200
        rjson = r.json()
        return rjson['data'][0]   
    else:
        return 'INVALID organization_id'

def get_meta_station_by_id(station_id,query_add = ''):
    if(type(station_id) is not str):
        return 'INVALID station_id (bad type)'
    if(len(station_id) != 24):
        return 'INVALID station_id (wrong length)'
    query = { '_id': station_id }
    if(query_add != ''):
        query.update(query_add)
    r = requests.get(url + 'stations', headers=headers, params=query)
    assert r.status_code == 200
    rjson = r.json()
    return rjson['data'][0]   

def get_meta_datastream_by_id(datastream_id,query_add = ''):
    if(type(datastream_id) is not str):
        return 'INVALID DATASTREAM_ID (bad type)'
    if(len(datastream_id) != 24):
        return 'INVALID DATASTREAM_ID (wrong length)'
    query = { '_id': datastream_id }
    if(query_add != ''):
        query.update(query_add)
    r = requests.get(url + 'datastreams', headers=headers, params=query)
    assert r.status_code == 200
    rjson = r.json()
    return rjson['data'][0]   

def get_meta_annotation(annotation_id,query_add = ''):
    if(type(annotation_id) is not str):
        return 'INVALID ANNOTATION_ID (bad type)'
    if(len(annotation_id) != 24):
        return 'INVALID ANNOTATION_ID (wrong length)'
    query = { '_id': annotation_id }
    if(query_add != ''):
        query.update(query_add)
    r = requests.get(url + 'annotations', headers=headers, params=query)
    assert r.status_code == 200
    rjson = r.json()
    return rjson['data'][0]   

# deprecated
def get_datastream_by_id(datastream_id,query_add = ''): 
    return get_meta_datastream_by_id(datastream_id,query_add)

def get_datastream_id_from_dsid(dsid,orgslug='all',station_id = ''):
    """translate SensorDB to Dendra ID"""
    # Legacy SensorDB used integer DSID (DatastreamID).  
    # This is a helper function to translate between Dendra datastream_id's and DSID's
    query = {'$limit':2016}

    # Narrow query to one station
    if(station_id != ''):
        query.update({'station_id':station_id})

    # Narrow query to one org or loop through all organizations
    org_list = list_organizations(orgslug)
    if(len(org_list) == 0): 
        print('ERROR: no organizations found with that acronym.')
        return ''
    # Build list of metadata 
    bigjson = {'data':[]}
    for org in org_list:
        orgid = org['_id']
        orgname = org['name']
        #print(orgname,orgid,query)
        query_org = query
        query_org.update({'organization_id': orgid})
        r = requests.get(url + 'datastreams', headers=headers, params=query)
        assert r.status_code == 200
        rjson = r.json()
        if(len(rjson['data']) > 0):
            bigjson['data'].extend(rjson['data'])
            #print(orgname,len(rjson['data']))
    dsid_list = []
    for ds in bigjson['data']:
        #print(ds['name'],ds['_id'])
        if('external_refs' not in ds):
            continue
        for ref in ds['external_refs']:
            if(ref['type'] == 'odm.datastreams.DatastreamID'):
                #print("\t",ref['type'], ref['identifier'])
                dsid_list.append([ref['identifier'],ds['_id']])
    for row in dsid_list:
        int_dsid = int(row[0])
        datastream_id = row[1]
        if(dsid == int_dsid):
            #print('FOUND!',dsid,int_dsid,datastream_id)
            return datastream_id



###########################################################
# Get Datapoints Functions
# these functions return timestamp,value pairs in a Pandas dataframe

def get_datapoints(datastream_id,begins_at,ends_before=time_format(),time_type='local',name='default'):
    """ GET Datapoints returns actual datavalues for only one datastream.  
    Returns a Pandas DataFrame columns. Both local and UTC time will be returned.
    Parameters: ends_before is optional. Defaults to now. time_type is optional default 'local', either 'utc' or 'local' 
    if you choose 'utc', timestamps must have 'Z' at the end to indicate UTC time."""

    if(type(datastream_id) is not str):
        return 'INVALID DATASTREAM_ID (bad type)'
    if(len(datastream_id) != 24):
        return 'INVALID DATASTREAM_ID (wrong length)'
    if(time_type == 'utc' and ends_before[-1] != 'Z'):
        ends_before += 'Z'
        
    query = {
        'datastream_id': datastream_id,
        'time[$gte]': begins_at,
        'time[$lt]': ends_before,
        '$sort[time]': "1",
        '$limit': "2016"
    } 
    if(time_type == 'utc'):
        time_col = 't'
    else:
        query.update({ 'time_local': "true" })
        time_col = 'lt'
        
    # Dendra requires paging of 2,000 records maximum at a time.
    # To get around this, we loop through multiple requests and append
    # the results into a single dataset.
    try:
        r = requests.get(url + 'datapoints', headers=headers, params=query)
        assert r.status_code == 200
    except:
        return r.status_code
    rjson = r.json()
    bigjson = rjson
    while(len(rjson['data']) > 0):
        df = pd.DataFrame.from_records(bigjson['data'])
        time_last = df[time_col].max()  # issue#1 miguel
        query['time[$gt]'] = time_last
        r = requests.get(url + 'datapoints', headers=headers, params=query)
        assert r.status_code == 200
        rjson = r.json()
        bigjson['data'].extend(rjson['data'])

    # Create Pandas DataFrame and set time as index
    # If the datastream has data for the time period, populate DataFrame
    if(len(bigjson['data']) > 0):
        df = pd.DataFrame.from_records(bigjson['data'])
    else:
        df = pd.DataFrame(columns={'lt','t','v'})
        
    # Get human readable name for data column
    if(name != 'default'):
        datastream_name = name
    else:
        datastream_meta = get_meta_datastream_by_id(datastream_id,{'$select[name]':1,'$select[station_id]':1})
        station_meta = get_meta_station_by_id(datastream_meta['station_id'],{'$select[slug]':1})
        stn = station_meta['slug'].replace('-',' ').title().replace(' ','')
        datastream_name = stn+'_'+datastream_meta['name'].replace(' ','_')
    
    # Rename columns
    df.rename(columns={'lt':'timestamp_local','t':'timestamp_utc','v':datastream_name},inplace=True)

    # Convert timestamp columns from 'object' to dt.datetime 
    df.timestamp_local = pd.to_datetime(df.timestamp_local, format='ISO8601') # format="%Y-%m-%dT%H:%M:%S")
    df.timestamp_utc   = pd.to_datetime(df.timestamp_utc, format='ISO8601', utc=True) # format="%Y-%m-%dT%H:%M:%S.000Z",utc=True)

    # Set index to timestamp local or utc 
    if(time_type == 'utc'):
        df.set_index('timestamp_utc', inplace=True, drop=True)  
    else:
        df.set_index('timestamp_local', inplace=True, drop=True)

    # Return DataFrame
    return df


def get_datapoints_from_id_list(datastream_id_list,begins_at,ends_before=time_format(),time_type='local'):
    """ GET Datapoints from List returns a dataframe of datapoints from a list of datastream ids. The function is 
    threaded for speed.  List must be an array of text variables which are datastream ids.  The first datastream
    on the list will create the time-index, so it is best if this one is the most complete of the list. If it has 
    time gaps, the rest of the dataframe can be compromised.  This may need to be changes in the future.
    All requirements of above get_datapoints apply to get_datapoints_from_list."""
    i = -1
    j = -1
    boo_new = True
    dftemp_list = [] # list of dataframes from the results

    with concurrent.futures.ThreadPoolExecutor() as executor:
        for dsid in datastream_id_list:
            i += 1
            future = executor.submit(get_datapoints,dsid,begins_at,ends_before,time_type,'default')
            dftemp_list.append(future)
            #print('in: ',i,datastream_id_list[i],dsid,future)

        for future in concurrent.futures.as_completed(dftemp_list):
            j +=1
            dftemp = future.result()
            #print('out"',j,datastream_id_list[j],dftemp,'type:',type(dftemp))
            # Check to see if any datapoints were returned.  
            # Many datastreams are not functional for the desired time frame.
            # If none, then skip the datastream and continue
            if(type(dftemp) is int):
                print(j,"ERROR: datastream failed to retrieve. check authentication or ID("+datastream_id_list[j]+")")
                continue
            elif(dftemp.empty):
                print("datastream ID("+datastream_id_list[j]+")  has no data for this time period. Skipping.")
                continue             
            # If there are datapoints, check to see if the dataframe has been created yet. 
            # If not, create, if so, add another column
            if(boo_new == True):
                df = dftemp
                boo_new = False
                print(j,dftemp.columns[1],'NEW dataframe created!')
            else:
                # Annotations are listed in a 'q' column. Remove for now.
                if('q' in dftemp.columns):
                    dftemp.drop('q',axis=1,inplace=True)
                # timestamp_utc column will be redundant if merged, so drop
                dftemp.drop('timestamp_utc',axis=1,inplace=True)
                df = df.merge(dftemp,how="left",left_index=True,right_index=True)
                print(j,dftemp.columns[0],'added.')
    return df

def get_datapoints_from_station_id(station_id,begins_at,ends_before=time_format(),time_type='local'):
    """ Returns a dataframe with ALL datastreams associated with a particular station for the time period """
    dlist = []
    ds_list = list_datastreams_by_station_id(station_id)
    for ds in ds_list:
        dlist.append(ds['_id'])
    df = get_datapoints_from_id_list(dlist,begins_at,ends_before,time_type)
    return df

# Deprecated        
# Lookup is an earlier attempt. Use get_datapoints unless you have to use this.    
def __lookup_datapoints_subquery(bigjson,query,endpoint='datapoints/lookup'):
    r = requests.get(url + endpoint, headers=headers, params=query)
    assert r.status_code == 200
    rjson = r.json()
    if(len(bigjson) == 0): # First pull assigns the metadata 
        bigjson = rjson
    else:  # all others just add to the datapoints
        for i in range(0,len(bigjson)):
            bigjson[i]['datapoints']['data'].extend(rjson[i]['datapoints']['data'])
    return bigjson

def lookup_datapoints(query,endpoint='datapoints/lookup',interval=5):    
    # Determine start and end timestamps
    # Start time
    #begins_at_original = dt.datetime.strptime(query['time[$gte]'],'%Y-%m-%dT%H:%M:%SZ')
    begins_at_original = parse(query['time[$gte]'])
    #begins_at_original = pytz.utc.localize(begins_at_original)
    # end time
    if('time[$lt]' in query):
        #ends_before_original = dt.datetime.strptime(query['time[$lt]'],'%Y-%m-%dT%H:%M:%SZ')
        ends_before_original = parse(query['time[$lt]'])
        #ends_before_original = pytz.utc.localize(ends_before_original)
    else: 
        ends_before_original_local = dt.datetime.now(tz.tzlocal())
        ends_before_original = ends_before_original_local.astimezone(pytz.utc)
    
    # Paging limit: 2016 records. 
    interval2k = (dt.timedelta(minutes=interval) * 2016 )

    # Perform repeat queries until the ends_before catches up with the target end date
    begins_at = begins_at_original
    ends_before = begins_at_original+interval2k
    bigjson = {}
    while(ends_before < ends_before_original and begins_at < ends_before_original):    
        bigjson = __lookup_datapoints_subquery(bigjson,query,endpoint)
        begins_at = ends_before
        ends_before = begins_at+interval2k 
    # One final pull after loop for the under 2016 records left
    bigjson = __lookup_datapoints_subquery(bigjson,query,endpoint)

    # Count total records pulled and update limit metadata
    max_records = pd.date_range(start=begins_at_original,end=ends_before_original, tz='UTC',freq=str(interval)+'min')
    for i in range(0,len(bigjson)):
        bigjson[i]['datapoints']['limit'] = len(max_records) 

    # return the full metadata and records
    return bigjson


###############################################################################
# Unit Tests
#
def __main():
    btime = True
    borg = False
    bstation = False
    bdatastream_id = False
    bdatapoints = True
    bdatapoints_lookup = False    

    ####################
    # Test Time
    if(btime == True):
        # time_utc converts string to datetime
        string_utc = '2019-03-01T08:00:00Z'
        print('UTC:',time_utc(string_utc))
        string_edt = '2019-03-01T08:00:00-0400'
        print('EDT:',time_utc(string_edt))
        string_hst = '2019-03-01T08:00:00HST'
        print('HST:',time_utc(string_hst))
        print('Empty (local default):',time_utc())
        
        # time_format converts datetime to utc string
        tu = dt.datetime.strptime(string_utc,'%Y-%m-%dT%H:%M:%SZ')
        print('time_format utc:',time_format(tu))
        te = dt.datetime.strptime(string_edt,'%Y-%m-%dT%H:%M:%S%z')
        print('time_format edt:',time_format(te))
        print('time_format empty:',time_format())
    
    
    ####################
    # Test Organizations
    if(borg == True):
        # Get One Organization ID 
        cdfw = get_organization_id('cdfw')
        print('List one Organization CDFW ID:',cdfw)

        # Get One Organization ID using list all function
        erczo = list_organizations('erczo')
        print('List Organizations ERCZO ID:',erczo[0]['_id'])

        # Get All Organization IDs        
        org_list = list_organizations()
        print('List All Organizations:')
        print("ID\t\t\tName")
        for org in org_list:
            print(org['_id'],org['name'])
        
        # Send a BAD Organization slug
        orgs = list_organizations('Trump_is_Evil')
        print('BAD List Organizations:',orgs)

        # Get Metadata for an organization
        orgslug = 'erczo'
        meta_erczo_slug = get_meta_organization(orgslug)
        print('Get metadata organization ERCZO slug:',meta_erczo_slug)
        erczoid = get_organization_id(orgslug)
        meta_erczo_id = get_meta_organization('',erczoid)
        print('Get metadata organization ERCZO ID:',meta_erczo_id)
    
    ####################    
    # Test stations
    if(bstation == True):
        # Get All stations
        st_list = list_stations()
        print('\nALL Organization Stations\n',st_list)
        
        # Get Stations from UCNRS only
        stslug = 'ucnrs'
        st_list = list_stations(stslug)
        #print(st_erczo)    
        print('\n',stslug.upper(),'Stations\n')
        print("ID\t\t\tName\t\tSlug")
        for station in st_list:
            print(station['_id'],station['name'],"\t",station['slug'])
        
        # Modify Query
        query_add = {'$select[station_type]':1}
        print(query_add)
        st_list = list_stations(stslug) #,query_add)
        print('\n',stslug.upper(),'Stations with station_type added\n',st_list)    
    
        # What happens when you send a BAD organization string?
        st_list = list_stations('Trump is Evil')
        print('\nBAD Organizations Stations\n',st_list)
     
    ####################    
    # Test Datastream from id
    if(bdatastream_id == True):
        # Get all Metadata about one Datastream 'South Meadow WS, Air Temp C'        
        airtemp_id = '5ae8793efe27f424f9102b87'
        airtemp_meta = get_meta_datastream_by_id(airtemp_id)
        print(airtemp_meta)
        
        # Get only Name from Metadata using query_add
        airtemp_meta = get_meta_datastream_by_id(airtemp_id,{'$select[name]':1})
        print(airtemp_meta)
                
    ####################        
    # Test Datapoints 
    if(bdatapoints == True):
        airtemp_id = '5ae8793efe27f424f9102b87'
        from_time = '2019-02-01T08:00:00Z' # UTC, not local PST time
        to_time = '2019-03-01T08:00:00Z'
        #to_time = None
        dd = get_datapoints(airtemp_id,from_time,to_time)
        dups = dd[dd.duplicated(keep=False)]
        print('get_datapoints count:',len(dd),'min date:',dd.index.min(),'max date:',dd.index.max())
        print('duplicates?\n',dups)
        
        # No end date
        to_time = None
        dd = get_datapoints(airtemp_id,from_time)
        print('get_datapoints end date set to now, count:',len(dd),'min date:',dd.index.min(),'max date:',dd.index.max())
        print(dd)
        
    ####################        
    # Test Datapoints Lookup 
    if(bdatapoints_lookup == True):
        # Parameters
        orgid = '58db17c424dc720001671378' # ucnrs
        station_id = '58e68cabdf5ce600012602b3'
        from_time = '2019-04-01T08:00:00Z' # UTC, not local PST time
        to_time = '2019-05-05T08:00:00Z'
        interval = 10 # 5,10,15
        
        tags = [
            'ds_Medium_Air',
            'ds_Variable_Temperature',
            'ds_Aggregate_Average'
        ]
        query = {
            'station_id': station_id,
            'time[$gte]': from_time,
            'tags': '.'.join(tags),
            '$sort[time]': 1,
            'time_local': 1,
            '$limit': 2000
        }
        if('to_time' in locals()):
        	query['time[$lt]'] = to_time
        #print(query)
        # Test the Query
        bigjson = lookup_datapoints(query,'datapoints/lookup',interval)
        
        # Show the results
        for doc in bigjson:
            print(doc['name'],len(doc['datapoints']['data']),doc['datapoints']['limit'],doc['_id'])

if(__name__ == '__main__'):
    __main()