# -*- coding: utf-8 -*-
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
        for n in xrange(8):
            out += str(uuid.uuid4())
        return out
        
    def is_sysadmin(self, user_data):
        return user_data.name == 'oudy'

    def checkUser(self, user_data):
        try:
            user = plugins.toolkit.get_action('user_show')(
                {'return_minimal': True,
                 'keep_sensitive_data': True,
                 'keep_email': True},
                {'id': user_data.name}
            )
        except plugins.toolkit.ObjectNotFound:
            pass
            user = None
        if user:
            # update the user in ckan only if ckan data is not matching drupal data
            update = False
            if user_data.mail != user['email']:
                update = True
            if self.is_sysadmin(user_data) != user['sysadmin']:
                update = True
            if update:
                user['email'] = user_data.mail
                user['sysadmin'] = self.is_sysadmin(user_data)
                user['id'] = user_data.name
                user = plugins.toolkit.get_action('user_update')({'ignore_auth': True}, user)
        else:
            user = {'email': user_data.mail,
                    'name': user_data.name,
                    'password': self.make_password(),
                    'sysadmin': self.is_sysadmin(user_data)}
            user = plugins.toolkit.get_action('user_create')({'ignore_auth': True}, user)
        plugins.toolkit.c.user = user['name']

        return user

    def index(self):
        extra_vars = {}

        data = request.POST

        if 'username' in data and 'password' in data and data['password']!='':
            login = data['username']
            password = data['password']
            extra_vars = {'data': data, 'errors': {}, 'username': data['username']}

            user = {'email': 'oudy1st@gmail.com',
                    'name': data['username'],
                    'password': self.make_password(),
                    'sysadmin': self.is_sysadmin(data['username']) }
                    
            cUser = self.checkUser(user)

            if cUser != None:
                session['oic-user'] = cUser['name']
                session.save()

            return toolkit.redirect_to('user.logged_in')

        elif 'username' in data:
            extra_vars = {'data': data, 'errors': {}, 'username': data['username']}

        else:
            extra_vars = {'data': {}, 'errors': {}, 'username': ''}

        return base.render('user/oiclogin3.html', extra_vars=extra_vars)