# -*- coding: utf-8 -*-
import ckan.plugins as plugins
import ckan.lib.helpers as helpers
import ckan.logic as logic
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.model as model
import logging
from ckan.common import g

import ckan.lib.base as base

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

    def login(self):
        #extra_vars = {}
        #return render('home/oiclogin.html', extra_vars=extra_vars)
        group_type = 'organization'
        is_organization = True
        extra_vars = {}
        page = h.get_page_number(request.params) or 1
        items_per_page = int(config.get(u'ckan.datasets_per_page', 20))

        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'for_view': True,
            u'with_private': False
        }

        try:
            _check_access(u'site_read', context)
            _check_access(u'group_list', context)
        except NotAuthorized:
            base.abort(403, _(u'Not authorized to see this page'))

        q = request.params.get(u'q', u'')
        if q=='':
            extra_vars["page"] = h.Page([], 0)
            extra_vars["group_type"] = group_type
            return base.render(
                _get_group_template(u'index_template', group_type), extra_vars)
        sort_by = request.params.get(u'sort')

        # TODO: Remove
        # ckan 2.9: Adding variables that were removed from c object for
        # compatibility with templates in existing extensions
        g.q = q
        g.sort_by_selected = sort_by

        extra_vars["q"] = q
        extra_vars["sort_by_selected"] = sort_by

        # pass user info to context as needed to view private datasets of
        # orgs correctly
        if g.userobj:
            context['user_id'] = g.userobj.id
            context['user_is_admin'] = g.userobj.sysadmin

        try:
            data_dict_global_results = {
                u'all_fields': False,
                u'q': q,
                u'sort': sort_by,
                u'type': group_type or u'group',
            }
            global_results = _action(u'group_list')(context,
                                                    data_dict_global_results)
        except ValidationError as e:
            if e.error_dict and e.error_dict.get(u'message'):
                msg = e.error_dict['message']
            else:
                msg = str(e)
            h.flash_error(msg)
            extra_vars["page"] = h.Page([], 0)
            extra_vars["group_type"] = group_type
            return base.render(
                _get_group_template(u'index_template', group_type), extra_vars)

        data_dict_page_results = {
            u'all_fields': True,
            u'q': q,
            u'sort': sort_by,
            u'type': group_type or u'group',
            u'limit': items_per_page,
            u'offset': items_per_page * (page - 1),
            u'include_extras': True
        }
        page_results = _action(u'group_list')(context, data_dict_page_results)

        extra_vars["page"] = h.Page(
            collection=global_results,
            page=page,
            url=h.pager_url,
            items_per_page=items_per_page, )

        extra_vars["page"].items = page_results
        extra_vars["group_type"] = group_type

        # TODO: Remove
        # ckan 2.9: Adding variables that were removed from c object for
        # compatibility with templates in existing extensions
        g.page = extra_vars["page"]
        return base.render(
            _get_group_template(u'index_template', group_type), extra_vars)


    def index(self):
        extra_vars = {}
        return base.render('home/oiclogin.html', extra_vars=extra_vars)