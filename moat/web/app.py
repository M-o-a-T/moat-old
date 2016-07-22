#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2016 by Matthias Urlichs <matthias@urlichs.de>,
##  it is licensed under the GPLv3. See the file `README.rst` for details,
##  including optimistic statements by the author.
##
##  This program is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License (included; see the file LICENSE)
##  for more details.
##
##  This header is auto-generated and may self-destruct at any time,
##  courtesy of "make update". The original is in ‘scripts/_boilerplate.py’.
##  Thus, do not remove the next line, or insert any blank lines above.
##BP

import logging

from flask import Flask, request, render_template, render_template_string, g, session, Markup, Response
from time import time
import os

from hamlish_jinja import HamlishExtension

import formalchemy.config
from jinja2 import Template
from formalchemy.templates import TemplateEngine
class JinjaEngine(TemplateEngine):
	def render(self, template, **kw):
		return Markup(render_template(os.path.join('formalchemy',template+'.haml'),**kw))

logger = logging.getLogger(__name__)

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

