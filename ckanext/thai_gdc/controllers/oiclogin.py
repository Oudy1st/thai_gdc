# -*- coding: utf-8 -*-
import ckan.plugins as p
import ckan.lib.helpers as helpers
from pylons import config
import ckan.logic as logic
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.model as model
import ckan.lib.uploader as uploader
import six
import logging
import sys
import locale
import pandas as pd
import numpy as np
import re
from ckanapi import LocalCKAN
import datetime
import ckan.lib.base as base

import uuid
import ckan.plugins.toolkit as toolkit

from ckan.plugins.toolkit import (
    _, c, h, BaseController, check_access, NotAuthorized, abort, render,
    redirect_to, request,
    )

from ckan.controllers.home import CACHE_PARAMETERS
import ckan.logic.schema as schema_

_validate = dict_fns.validate
ValidationError = logic.ValidationError
NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized

log = logging.getLogger(__name__)

reload(sys)
sys.setdefaultencoding("utf-8")

class OICLoginController(p.toolkit.BaseController):

    def login(self):
        data = request.POST
        extra_vars = {}
        return render('home/oiclogin.html', extra_vars=extra_vars)
