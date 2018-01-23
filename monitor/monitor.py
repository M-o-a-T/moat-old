#!/usr/bin/python3
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

#from moat import patch; moat.patch()
import qbroker; qbroker.setup(gevent=True)
from qbroker.util.async import Main
import asyncio

import gtk
import gtk.gdk
import gnome.ui
import gtk.glade
import gobject
import glib
import os
from time import time
from datetime import datetime

APPNAME="monitor"
APPVERSION="0.1"

class Monitor(object):
	def __init__(self, widgets):
		self.widgets = widgets
		widgets.MonitorData = self
	

class MonitorUI(object):
	def __init__(self):
		#self._init_acctcache()

		gnome.init(APPNAME, APPVERSION)
		self.widgets = gtk.glade.XML(APPNAME+".glade")

		d = MonitorUI.__dict__.copy()
		for k in d.keys():
			d[k] = getattr(self,k)
		self.widgets.signal_autoconnect(d)
		self.events = {}
		self._init_events()
		#self.enable_stuff()

	def init_done(self):
		self['main'].show_all()

	def __getitem__(self,name):
		return self.widgets.get_widget(name)

	def _init_events(self):
		v = self['events_view']
		s = v.get_selection()
		s.set_mode(gtk.SELECTION_SINGLE)
		m = gtk.TreeStore(gobject.TYPE_STRING, gobject.TYPE_UINT, gobject.TYPE_PYOBJECT)
		# text counter time
		# time should be TYPE_FLOAT, but that doesn't work for some reason

		mm = gtk.TreeModelSort(m)

		def cmp(s,a,b):
			a=s.get(a,2)[0]
			b=s.get(b,2)[0]
			if a is None and b is None: return 0
			if a is None: return 1
			if b is None: return -1
			return a-b
		mm.set_sort_func(2,cmp)
		#mm.set_sort_column_id (-1, gtk.SORT_DESCENDING)

		v.set_model(mm)
		v.set_headers_visible(True)
		v.set_show_expanders(False)
		c = v.get_column(0)
		if c: v.remove_column(c)

		# create the TreeViewColumn to display the data
		def add(name,col,renderer=None, *renderer_args):
			r = gtk.CellRendererText()
			column = gtk.TreeViewColumn(name,r,text=col)
			if renderer:
				column.set_cell_data_func(r, renderer, renderer_args)
			v.append_column(column)
			column.set_sizing (gtk.TREE_VIEW_COLUMN_AUTOSIZE)
			column.set_resizable(True)
			column.set_reorderable(True)
			cell = gtk.CellRendererText()
			column.pack_start(cell, True)
# doesn't work for some reason. TODO.
#			def ClickMe(*a,**k):
#				print("Clicked",a,k)
#			column.connect("clicked", ClickMe,col)

		def DatePrinter(column, cell, model, iter, col_key):
			text = model.get_value(iter, 2)
			text = datetime.utcfromtimestamp(text)
			text = text.strftime("%Y-%m-%d %H:%M:%S.%.3f")
			ti = text.rfind('.')
			if ti>0 and len(ti)-ti > 4: # limit to msec
				text = text[:ti+4]
			cell.set_property("text", text)
		add('Event',0)
		add('#',1)
		add('zuletzt',2,DatePrinter)

	def add_event(self,name):
		v = self['events_view']

		m = v.get_model().get_model() # we want the unsorted master model that's not sorted
		tm=time()
		try:
			i = self.events[name]
		except KeyError:
			i = m.append(None,row=[name,1,tm])
			self.events[name] = i
		else:
			r, = m.get(i,1)
			m.set(i, 1,r+1, 2,tm)

###	EVENTS
	def on_main_destroy(self,window):
		# main window goes away
		gtk.main_quit()

	def on_main_delete_event(self,window,event):
		# True if the window should not be deleted
		return False

	def on_quit_button_clicked(self,x):
		gtk.main_quit()

	def on_menu_quit(self,x):
		gtk.main_quit()

	def on_menu_test(self,x):
		self.add_event("Test")
	def on_menu_test2(self,x):
		self.add_event("Test 2")

	def on_menu_prefs(self,x):
		self['prefs_status'].hide()
		self['prefs'].show()
	def on_prefs_delete_event(self,*x):
		self['prefs'].hide()
		return True

	def on_prefs_ok(self,*x):
		print("OK",x)
		self['prefs'].hide()
	def on_prefs_test(self,*x):
		print("TEST",x)
	def on_prefs_cancel(self,*x):
		print("CANCEL",x)
		self['prefs'].hide()
	def on_prefs_port_ins(self,*x):
		print("PI",x)
	def on_prefs_port_insa(self,*x):
		print("PIa",x)
	def on_prefs_port_pre(self,*x):
		print("PE",x)

class MonitorMain(Main):
	@asyncio.coroutine
	def at_start(self):
		yield from super().at_start()
		self.widgets = MonitorUI()
		MonitorData = Monitor(widgets)
		self.widgets.init_done()

if __name__ == "__main__":
	main=MonitorMain()
	main.run()

# END #
