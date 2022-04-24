# -*- coding: utf-8 -*-
from pickle import NONE
import ckan.plugins as plugins
import ckan.lib.helpers as helpers
import ckan.logic as logic
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.model as model
import logging
from ckan.common import g

import ckan.lib.base as base

from ckan.common import session
from ckan.model import Session
from ckan.plugins import toolkit

import uuid
import hashlib
import re
import requests
import json


from ckan.plugins.toolkit import (
    _, c, h, BaseController, check_access, NotAuthorized, abort, render,
    redirect_to, request,
    )

from ckan.controllers.home import CACHE_PARAMETERS

_validate = dict_fns.validate
ValidationError = logic.ValidationError

log = logging.getLogger(__name__)

class UserManageController(plugins.toolkit.BaseController):

    def user_active(self):
        data = request.GET
        if 'id' in data:
            try:
                data_dict = logic.clean_dict(
                    dict_fns.unflatten(
                        logic.tuplize_dict(
                            logic.parse_params(
                                request.GET, ignore_keys=CACHE_PARAMETERS))))
                
                context = {
                    u'model': model,
                    u'session': model.Session,
                    u'user': g.user,
                    u'auth_user_obj': g.userobj,
                    u'for_view': True
                }
                check_access('user_update', context, {})
                user_dict = plugins.toolkit.get_action('user_show')(None, {'id':data['id']})
                if user_dict and user_dict['state'] == 'deleted':
                    user = model.User.get(user_dict['name'])
                    user.state = model.State.ACTIVE
                    user.save()
                h.redirect_to(controller='user', action='read', id=data['id'])
            except logic.ValidationError as e:
                return e



class OICLoginController(plugins.toolkit.BaseController):


    @staticmethod
    def make_password():
        # create a hard to guess password
        out = ''
        for n in range(8):
            out += str(uuid.uuid4())
        return out
        
    def is_sysadmin(self, user_data):
        admin_emp_codes = toolkit.config['ckanext.oiclogin.admin_emp_codes']
        return user_data['employeeCode'] in admin_emp_codes

    def map_oicemail(self, prefix):
        #get config 
        mail_suffix = toolkit.config['ckanext.oiclogin.mail_suffix']
        # return prefix + mail_suffix
        return prefix+"@oic.com"

    def get_ckanuser(self, user):

        user_ckan = model.User.by_name(user)

        if user_ckan:
            user_dict = toolkit.get_action('user_show')(data_dict={'id': user_ckan.id})
            return user_dict
        else:
            return None

    def verify_user(self, username, password):
        
        url = toolkit.config['ckanext.oiclogin.url']

        # url = "https://6c459b75-7f8c-4755-8fc3-62b0e7b8e996.mock.pstmn.io/oiclogin"
        r = requests.post(url, json={"username": username, "password":password})
    
        if r.ok:
            content = json.loads(r.content)
            if content['result'] == "SUCCESS":
                return content
            else:
                return None
        else:
            return None

#             {
#     "asgOfficeCode": "",
#     "asgOfficeName": "",
#     "dsgOfficeCode": "",
#     "dsgOfficeName": "",
#     "departmentCode": "109000",
#     "departmentName": "ฝ่ายเทคโนโลยีสารสนเทศและการสื่อสาร",
#     "divisionCode": "109200",
#     "divisionName": "กลุ่มกลยุทธ์และบริหารข้อมูลด้านการประกันภัย",
#     "employeeCode": "62-1-054",
#     "employeeName": "นายธนานันท์   เขมวราภรณ์",
#     "mapDeptCode": "109200",
#     "mapDeptName": "กลุ่มกลยุทธ์และบริหารข้อมูลด้านการประกันภัย",
#     "positionCode": "2300",
#     "positionName": "เจ้าหน้าที่ชำนาญการ",
#     "result": "SUCCESS",
#     "sgOfficeCode": "100000",
#     "sgOfficeName": "เลขาธิการ",
#     "sectionCode": "",
#     "sectionName": ""
# }

    def index(self):
        extra_vars = {}

        data = request.POST

        if 'username' in data and 'password' in data and data['password']!='':



            username = data['username']
            password = data['password']
            extra_vars = {'data': data, 'errors': {}, 'username': username }

            login_data = self.verify_user(username, password)
            
            # for debug 
            if username == "testuser":
                login_data['employeeCode'] = "62-1-050"


            if login_data != None:
                oic_id = login_data['employeeCode']
                oic_email = self.map_oicemail(data['username'])
                oic_username = 'oic-'+login_data['employeeCode']
                oic_fullname = login_data['employeeName']
                oic_sysadmin = self.is_sysadmin(login_data)
                users = toolkit.get_action('user_list')(data_dict=dict(q=oic_username), context={'ignore_auth': True})
                # users = toolkit.get_action('user_list')(data_dict=dict(email=oic_email), context={'ignore_auth': True})
                

                if len(users) == 1:
                    user = users[0]
                    # update the user in ckan only if ckan data is not matching drupal data
                    update = False
                    if oic_sysadmin != user['sysadmin']:
                        update = True
                        
                    if oic_fullname != user['fullname']:
                        update = True

                    if update:
                        user_update = toolkit.get_action('user_update')
                        user['fullname'] = oic_fullname
                        user['sysadmin'] = oic_sysadmin
                        user['id'] = oic_id
                        user = user_update({'ignore_auth': True}, user)
                elif len(users) == 0:
                    user_create = toolkit.get_action('user_create')
                    user = {'id': oic_id,
                            'email': oic_email,
                            'name': oic_username,
                            'fullname': oic_fullname,
                            'password': str(uuid.uuid4()),
                            'sysadmin': oic_sysadmin}
                    user = user_create(context={'ignore_auth': True}, data_dict=user)
                else:
                    raise Exception("Found invalid number of users with this username {}".format(username))

                session['ckanext-oic-user'] = user['name']
                session.save()

                # return toolkit.redirect_to(controller='user', action='dashboard')
                return toolkit.redirect_to('user.logged_in')

            else:
                extra_vars = {'data': data, 'errors': {}, 'error_message': 'Invalid username or password', 'username': data['username']}

        # elif 'username' in data:
        #     login_data = self.verify_user('username', 'password')
        #     if login_data != None:
                
        #         if data['username'] == 'testuser' or data['username'] == 'testuser2':
        #             login_data['employeeCode'] = '62-1-050'
        #         if data['username'] == 'testuser3':
        #             login_data['employeeCode'] = '62-1-055'

        #         oic_email = self.map_oicemail(data['username'])
        #         oic_username = 'oic_'+login_data['employeeCode']
        #         oic_fullname = login_data['employeeName']
        #         oic_org = login_data['departmentName']
        #         oic_sysadmin = self.is_sysadmin(login_data)
                
        #         user_create = toolkit.get_action('user_create')
        #         try:

        #             if data['username'] == 'testuser1':
        #                 users = toolkit.get_action('user_list')(data_dict=dict(email=oic_email), context={'ignore_auth': True})
        #                 if len(users) > 0:
        #                     extra_vars = {'data': data, 'errors': {}, 'error_message':'find email', 'username': ''}
        #                 else:
        #                     user = {
        #                             'id': 1,
        #                             'email': 'testuser1@test.com',
        #                             'fullname': oic_fullname,
        #                             'password': str(uuid.uuid4()),
        #                             'sysadmin': False
        #                             }
        #                     user = user_create(context={'ignore_auth': True}, data_dict=user)   
        #                     extra_vars = {'data': data, 'errors': {}, 'error_message':'not find email', 'username': ''}
                        
        #             elif data['username'] == 'testuser2':
        #                 users = toolkit.get_action('user_list')(data_dict=dict(q=oic_username), context={'ignore_auth': True})
        #                 if len(users) > 0:
        #                     extra_vars = {'data': data, 'errors': {}, 'error_message':'find id', 'username': ''}
        #                 else:
        #                     user = {
        #                             'id': 2,
        #                             'email': 'testuser2@test.com',
        #                             'fullname': oic_fullname,
        #                             'password': str(uuid.uuid4()),
        #                             'sysadmin': oic_sysadmin
        #                             }
        #                     user = user_create(context={'ignore_auth': True}, data_dict=user)   
        #                     extra_vars = {'data': data, 'errors': {}, 'error_message':'not find id', 'username': ''}
        #             elif data['username'] == 'testuser3':
        #                 users = toolkit.get_action('user_list')(data_dict=dict(q=oic_username), context={'ignore_auth': True})
        #                 if len(users) > 0:
        #                     extra_vars = {'data': data, 'errors': {}, 'error_message':'find id', 'username': ''}
        #                 else:
        #                     user = {
        #                             'id': 3,
        #                             'email': 'testuser3@oic.or.th',
        #                             'fullname': oic_fullname,
        #                             'password': str(uuid.uuid4()),
        #                             'sysadmin': oic_sysadmin
        #                             }
        #                     user = user_create(context={'ignore_auth': True}, data_dict=user)   
        #                     extra_vars = {'data': data, 'errors': {}, 'error_message':'not find id', 'username': ''}
                            
        #             elif self.is_sysadmin(login_data):
        #                 users = toolkit.get_action('user_list')(data_dict=dict(email=oic_email), context={'ignore_auth': True})
        #                 extra_vars = {'data': data, 'errors': {}, 'error_message':'admin-' + oic_email, 'username': ''}
        #             else:
        #                 extra_vars = {'data': data, 'errors': {}, 'error_message':'user-' + oic_email, 'username': ''}
                        
        #         except toolkit.ObjectNotFound:
        #             extra_vars = {'data': data, 'errors': {}, 'error_message':oic_email + admin_emp_codes, 'username': ''}
        #     else:
        #         extra_vars = {'data': data, 'errors': {}, 'error_message':'api fail', 'username': data['username']}

        else:
            extra_vars = {'data': {}, 'errors': {}, 'error_message': 'กรุณากรอกข้อมูลเพื่อเข้าสู่ระบบ', 'username': ''}

        return base.render('user/oiclogin3.html', extra_vars=extra_vars)