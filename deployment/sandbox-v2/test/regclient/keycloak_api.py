# File containing API calls to Keycloak

import datetime as dt
import requests
import json
import base64
import os
import secrets
import sys
import secrets
import hashlib
sys.path.insert(0, '../')
from utils import *

class KeycloakSession:
    def __init__(self, server, admin, admin_pwd):
        self.server = server
        self.token = self.get_auth_token(admin, admin_pwd)
    
    def get_auth_token(self, admin, admin_pwd):
        url = 'https://%s/keycloak/auth/realms/master/protocol/openid-connect/token' % self.server
        j = {
            'username': admin,
            'password': admin_pwd,
            'grant_type': 'password',
            'client_id': 'admin-cli'
        }
        
        r = requests.post(url, data=j)
        r = response_to_json(r)
        return  r['access_token']
  
    def create_user(self, realm_id, name, pwd, email, first_name, last_name): 
        url =  'https://%s/keycloak/auth/admin/realms/%s/users' % (self.server, realm_id)
        headers = {
           'Authorization' : 'Bearer %s' % self.token,
           'Content-type' : 'application/json',
           'Accept': 'application/json'
        }
        j = {
            'id': '',
            'username': name,
            'email': email,
            'enabled': True,
            'emailVerified': False,
            'firstName': first_name,
            'lastName': last_name,
            'credentials': [
                {
                    'type': 'password',
                    'value': pwd,
                    'temporary': False
                }
            ],
            'attributes': {
              'userPassword': salted_password(pwd)  # Needed for reg client
            }
        } 
        r = requests.post(url, headers=headers, json = j)
        return r

    def update_user(self, realm_id, name, pwd, email, first_name, last_name, user_id): 
        url =  'https://%s/keycloak/auth/admin/realms/%s/users/%s' % (self.server, realm_id, user_id)

        headers = {
           'Authorization' : 'Bearer %s' % self.token,
           'Content-type' : 'application/json',
           'Accept': 'application/json'
        }
        j = {
            'id': '',
            'username': name,
            'email': email,
            'enabled': True,
            'emailVerified': False,
            'firstName': first_name,
            'lastName': last_name,
            'credentials': [
                {
                    'type': 'password',
                    'value': pwd,
                    'temporary': False
                }
            ],
            'attributes': {
              'userPassword': salted_password(pwd)  # Needed for reg client
            }
        } 
        r = requests.put(url, headers=headers, json = j)
        return r

    def get_user(self, realm_id, name):  # Get user by username
        '''
        Returns user id.
        '''
        url =  'https://%s/keycloak/auth/admin/realms/%s/users?username=%s' % (self.server, realm_id, name)

        headers = {
           'Authorization' : 'Bearer %s' % self.token,
           'Content-type' : 'application/json',
           'Accept': 'application/json'
        }
        r = requests.get(url, headers=headers)
        r = response_to_json(r) 
        user_id = r[0]['id']
        return user_id
    
    def get_role(self, realm_id, rolename):
        url =  'https://%s/keycloak/auth/admin/realms/%s/roles/%s' % (self.server, realm_id, rolename)
        headers = {
           'Authorization' : 'Bearer %s' % self.token,
           'Content-type' : 'application/json',
           'Accept': 'application/json'
        }
        r = requests.get(url, headers=headers)
        return r

    def map_user_role(self, realm_id, user_id, role_json):
        url = 'https://%s/keycloak/auth/admin/realms/%s/users/%s/role-mappings/realm' % (self.server, realm_id, user_id)
        headers = {
           'Authorization' : 'Bearer %s' % self.token,
           'Content-type' : 'application/json',
           'Accept': 'application/json'
        }
        r = requests.post(url, headers=headers, json = [role_json]) # Keycloak api expects list
        return r


def salted_password(pwd):
    '''
    Generates a random salt of 8 bytes, appends to original password and generates a SHA256 hash.
    Appends salt bytes to hashed output and further base64 encodes the final output.
    '''

    salt = secrets.token_bytes(8) 
    h = hashlib.sha256()
    h.update(pwd.encode() + salt)
    salted_hash = h.digest()  # type bytes
    salted_hash = salted_hash + salt  # Append salt
    salted_hash = base64.b64encode(salted_hash)  # type bytes
    salted_hash = '{SSHA256}'+salted_hash.decode()
    b64_salted_hash = base64.b64encode(salted_hash.encode()).decode()  # bytes -> str
    return b64_salted_hash


