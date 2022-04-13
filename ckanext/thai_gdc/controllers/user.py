# -*- coding: utf-8 -*-
import ckan.plugins as plugins
import ckan.lib.helpers as helpers
import ckan.logic as logic
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.model as model
import logging
from ckan.common import g

import ckan.lib.base as base

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

    def index(self):
        extra_vars = {}

        return base.render('user/oiclogin.html', extra_vars=extra_vars)
        
    def index2(self):
        extra_vars = {}

        return base.render('user/oiclogin2.html', extra_vars=extra_vars)

    def index3(self):
        extra_vars = {}

        data = request.POST

        if 'username' in data:
            extra_vars = {'data': data, 'errors': {}, 'username': data['username']}

            # if data['username'] == 'oudy':
            request.session['oic_user'] = "session" + data['username'] 
        elif request.session['oic_user'] != '':
            extra_vars = {'data': data, 'errors': {}, 'username': request.session['oic_user']}
        else:
            extra_vars = {'data': {}, 'errors': {}, 'username': ''}

        return base.render('user/oiclogin3.html', extra_vars=extra_vars)