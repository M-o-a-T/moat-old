#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
## This file is part of noris network AG's "zuko" package.
##
## noris-zuko is Copyright © 2014 by Matthias Urlichs <matthias@urlichs.de>.
## and noris network AG, Nürnberg, Germany. All rights reserved.
##
## This paragraph is auto-generated and may self-destruct at any time,
## courtesy of "make update". The original is in ‘utils/_boilerplate.py’.
## Thus, please do not remove the next line, or insert any blank lines.
##BP

import logging

from flask import Flask, request, render_template, render_template_string, g, session, Markup, Response
from time import time
import os

from hamlish_jinja import HamlishExtension

from zuko import config
from zuko.main import Main
from zuko.base import init_logging
from zuko.web.sockets import Sockets

import formalchemy.config
from jinja2 import Template
from formalchemy.templates import TemplateEngine
class JinjaEngine(TemplateEngine):
	def render(self, template, **kw):
		return Markup(render_template(os.path.join('formalchemy',template+'.haml'),**kw))

logger = logging.getLogger('zuko.tools.webserver')

###################################################
# web server setup

class HamlFlask(Flask):
	def create_jinja_environment(self):
		"""Add support for .haml templates."""
		rv = super(HamlFlask,self).create_jinja_environment()
 
		rv.extensions["jinja2.ext.HamlishExtension"] = HamlishExtension(rv)
		rv.hamlish_file_extensions=('.haml',)
		rv.hamlish_mode='debug'
		rv.hamlish_enable_div_shortcut=True

		rv.filters['datetime'] = datetimeformat

		return rv

	def select_jinja_autoescape(self, filename):
		"""Returns `True` if autoescaping should be active for the given
		template name.

		.. versionadded:: 0.5
		"""
		if filename is None:
			return False
		if filename.endswith('.haml'):
			return True
		return super(HamlFlask,self).select_jinja_autoescape(filename)

def datetimeformat(value, format='%d-%m-%Y %H:%M %Z%z'):
	if isinstance(value,(int,float)):
		value = datetime.utcfromtimestamp(value)
	return value.astimezone(TZ).strftime(format)

app = HamlFlask(__name__, template_folder=os.path.join(os.getcwd(),'web','templates'), static_folder=os.path.join(os.getcwd(),'web','static'))

##################################################

class CustomProxyFix(object):
	def __init__(self, app):
		self.app = app
	def __call__(self, environ, start_response):
		host = environ.get('HTTP_X_FORWARDED_HOST', '')
		if host:
			environ['HTTP_HOST'] = host
		return self.app(environ, start_response)

app.wsgi_app = CustomProxyFix(app.wsgi_app)

def setup_app(main=None):
	app.config.from_object(config)
	websockets = Sockets(app)

	from moat.web import ui,admin,user,monitor
	from moat.web.util import register as web_register
	web_register(app)
	ui.register(app)
	admin.register(app)
	user.register(app)
	if main is not None:
		monitor.register(app,websockets,main)

