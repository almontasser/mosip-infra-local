#!/bin/python3

import sys
import argparse
from api import *
import csv
import json
import config as conf
sys.path.insert(0, '../')
from utils import *

def add_partner(csv_file,):
    session = MosipSession(conf.server, conf.partner_user, conf.partner_pwd, 'partner', ssl_verify=conf.ssl_verify)
    reader = csv.DictReader(open(csv_file, 'rt')) 
    for row in reader:
        myprint('Adding partner %s' % row['name'])
        r = session.add_partner(row['name'], row['contact'], row['address'], row['email'], row['id'], 
                                    row['type'], row['policy_group'])
        myprint(r)

def add_policy_group(csv_file):
    session = MosipSession(conf.server, conf.policym_user, conf.policym_pwd, 'partner', ssl_verify=conf.ssl_verify)
    reader = csv.DictReader(open(csv_file, 'rt')) 
    for row in reader:
        myprint('Adding policy group %s' % row['name'])
        r = session.add_policy_group(row['name'], row['description'])
        myprint(r)
        if len(r['errors']) > 0:  
            if r['errors'][0]['errorCode'] == 'PMS_POL_014': # Policy group already exists
                continue

def get_policy_group_id(policy_group_name):
        session = MosipSession(conf.server, conf.policym_user, conf.policym_pwd, 'partner', ssl_verify=conf.ssl_verify)
        r = session.get_policy_groups() 
        policy_groups = r['response']
        pg_id = None
        for pg in policy_groups:
             if pg['policyGroup']['name'] == policy_group_name:
                 pg_id = pg['policyGroup']['id']
                 break 
        return pg_id

def get_policy_id(policy_name):
    session = MosipSession(conf.server, conf.policym_user, conf.policym_pwd, 'partner', ssl_verify=conf.ssl_verify)
    r = session.get_policies() 
    policies =  r['response']
    policy_id = None
    for policy in policies:
        if policy['policyName'] == policy_name:
            policy_id = policy['policyId']
    return policy_id

def add_policy(csv_file):
    session = MosipSession(conf.server, conf.policym_user, conf.policym_pwd, 'partner', ssl_verify=conf.ssl_verify)
    reader = csv.DictReader(open(csv_file, 'rt')) 
    for row in reader:
        myprint('Adding policy "%s"' % row['name'])
        json_str = open(row['policy_file'], 'rt').read() 
        policy = json.loads(json_str)  
        r = session.add_policy(row['policy_id'],row['name'], row['description'], policy, row['policy_group'], 
                               row['policy_type'])
        myprint(r)
        if len(r['errors']) == 0:  
            policy_id = r['response']['id']
        else:
            if r['errors'][0]['errorCode'] == 'PMS_POL_009':  # Policy exists
                myprint('Updating policy "%s"' % row['name'])
                policy_id = get_policy_id(row['name'])
                if policy_id is None:
                    myprint('Policy id for policy "%s" could not be found, skipping..' % row['name'])
                    continue
                r = session.update_policy(row['name'], row['description'], policy, row['policy_group'], 
                                          row['policy_type'], policy_id)
                myprint(r) 
            else:
                continue  # Can't do much
        
        # publish policy 
        myprint('Getting policy group id for policy group "%s"' % row['policy_group'])
        pg_id = get_policy_group_id(row['policy_group'])
        if pg_id is None:
            myprint('Could not find id for policy group "%s"' % (row['policy_group']))
            continue
        myprint('Publishing policy "%s"' % row['name'])
        r = session.publish_policy(pg_id, policy_id)
        myprint(r)

def upload_ca_certs(csv_file):
    session = MosipSession(conf.server, conf.partner_manager_user, conf.partner_manager_pwd, 'partner', 
                           ssl_verify=conf.ssl_verify)
    reader = csv.DictReader(open(csv_file, 'rt')) 
    for row in reader:
        myprint('Uploading CA certificate "%s"' % row['ca_cert_path'])
        cert_data = open(row['ca_cert_path'], 'rt').read()
        r = session.upload_ca_certificate(cert_data, row['partner_domain'])
        myprint(r)

def upload_partner_certs(csv_file):
    session = MosipSession(conf.server, conf.partner_user, conf.partner_pwd, 'partner', ssl_verify=conf.ssl_verify)
    reader = csv.DictReader(open(csv_file, 'rt')) 
    for row in reader:
        myprint('Uplading partner certificate for "%s"' % row['org_name'])
        cert_data = open(row['cert_path'], 'rt').read()
        r = session.upload_partner_certificate(cert_data, row['org_name'], row['partner_domain'], 
                                               row['partner_id'], row['partner_type'])
        myprint(r)
        mosip_signed_cert_path = os.path.join(os.path.dirname(row['cert_path']), 'mosip_signed_cert.pem')
        if r['errors'] is None:
            mosip_signed_cert = r['response']['signedCertificateData']
            open(mosip_signed_cert_path, 'wt').write(mosip_signed_cert)
            myprint('MOSIP signed certificate saved as %s' % mosip_signed_cert_path)

def map_partner_policy(csv_file):
    session1 = MosipSession(conf.server, conf.partner_user, conf.partner_pwd, 'partner', ssl_verify=conf.ssl_verify)
    session2 = MosipSession(conf.server, conf.partner_manager_user, conf.partner_manager_pwd, 'partner', 
                            ssl_verify=conf.ssl_verify)
    reader = csv.DictReader(open(csv_file, 'rt')) 
    for row in reader:
        myprint('Getting policies for a partner "%s" to check if this is a duplicate entry' % row['partner_id']) 
        r = session1.get_partner_api_key_requests(row['partner_id'], row['policy_name'], row['description'])
        myprint(r)
        if r['errors'] is not None:  
            if r['errors']['errorCode'] == 'PMS_PRT_005':  # Partner does not exist, add only then
                myprint('Sending partner-policy mapping request for (PARTNER: %s, POLICY: %s)' % (row['partner_id'], 
                         row['policy_name']))
                r = session1.add_partner_api_key_requests(row['partner_id'], row['policy_name'], row['description'])
                myprint(r)
                api_request_id = r['response']['apiRequestId']
        
                # Approve
                myprint('Approving request for (PARTNER: %s, POLICY: %s)' % (row['partner_id'], row['policy_name']))
                r =  session2.approve_partner_policy(api_request_id, 'Approved')
                myprint(r)
        else:
            if r['response'][0]['apiKeyRequestStatus'] == 'In-Progress':
                api_request_id = r['response'][0]['apiKeyReqID']
                myprint('Approving request for (PARTNER: %s, POLICY: %s)' % (row['partner_id'], row['policy_name']))
                r =  session2.approve_partner_policy(api_request_id, 'Approved')
                myprint(r)
            else:
                myprint('ERROR: Skipping..')
                continue

def create_misp(csv_file):
    session = MosipSession(conf.server, conf.misp_user, conf.misp_pwd, 'partner', ssl_verify=conf.ssl_verify)
    reader = csv.DictReader(open(csv_file, 'rt')) 
    for row in reader:
        myprint('Creating MISP "%s"' % row['org_name'])
        r = session.create_misp(row['org_name'], row['address'], row['contact'], row['email'])
        myprint(r)
        if len(r['errors']) == 0:   # No error
            misp_id = r['response']['mispID']
        else: 
            myprint('Get misp id for "%s"' % row['org_name'])
            if r['errors'][0]['errorCode'] == 'PMS_MSP_003':  # Already exists 
                r = session.get_misps() 
                misps = r['response'] 
                for misp in misps:
                    myprint(misp)
                    if misp['misp']['name'] == row['org_name']:
                        misp_id = misp['misp']['ID']
            else:
               continue # Can't do much but to myprint error 
        # Approving 
        myprint('Approving MISP "%s"' % row['org_name'])
        r = session.approve_misp(misp_id, 'approved')
        myprint(r)

def add_extractor(csv_file):
    session = MosipSession(conf.server, conf.partner_user, conf.partner_pwd, ssl_verify=conf.ssl_verify)
    reader = csv.DictReader(open(csv_file, 'rt')) 
    for row in reader:
        myprint('Adding extractor for %s -- %s' % (row['partner_id'], row['policy_id']))
        r = session.add_extractor(row['partner_id'], row['policy_id'], row['attribute'], row['biometric'], 
                                  row['provider'], row['version'])
        myprint(r)

def args_parse(): 
   parser = argparse.ArgumentParser()
   parser.add_argument('action', help='policy_group|policy|extractor|partner|upload_certs|partner_policy|misp|all') 
   parser.add_argument('--server', type=str, help='Full url to point to the server.  Setting this overrides server specified in config.py')
   parser.add_argument('--disable_ssl_verify', help='Disable ssl cert verification while connecting to server', action='store_true')
   args = parser.parse_args()
   return args, parser

def main():
    args, parser =  args_parse() 

    if args.server:
        conf.server = args.server   # Overide

    if args.disable_ssl_verify:
        conf.ssl_verify = False

    init_logger('./out.log')
    try:
        if args.action == 'policy_group' or args.action == 'all':
            add_policy_group(conf.csv_policy_group)
        if args.action == 'policy' or args.action == 'all':
            add_policy(conf.csv_policy)
        if args.action == 'partner' or args.action == 'all':
            add_partner(conf.csv_partner)
        if args.action == 'extractor' or args.action == 'all':
            add_extractor(conf.csv_extractor)
        if args.action == 'upload_certs' or args.action == 'all':
            upload_ca_certs(conf.csv_partner_ca_certs) 
            upload_partner_certs(conf.csv_partner_certs) #TODO: make sure  key_alias.py is called below api
        if args.action == 'partner_policy' or args.action == 'all':   
            map_partner_policy(conf.csv_partner_policy_map)
        if args.action == 'misp'or args.action == 'all':
            create_misp(conf.csv_misp)
    except:
        formatted_lines = traceback.format_exc()
        myprint(formatted_lines)
        sys.exit(1)

    return sys.exit(0)

if __name__=="__main__":
    main()
