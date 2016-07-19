# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2015 by Matthias Urlichs <matthias@urlichs.de>,
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

from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from rainman import admin as rain_admin
from irrigator.views.site import SiteView,SitesView,SiteNewView,SiteEditView,SiteDeleteView
from irrigator.views.controller import ControllerView,ControllersView,ControllerNewView,ControllerEditView,ControllerDeleteView
from irrigator.views.feed import FeedView,FeedsView,FeedNewView,FeedEditView,FeedDeleteView
from irrigator.views.valve import ValveView,ValvesView,ValveNewView,ValveEditView,ValveDeleteView
from irrigator.views.envgroup import EnvGroupView,EnvGroupsView,EnvGroupNewView,EnvGroupEditView,EnvGroupDeleteView
from irrigator.views.level import LevelView,LevelsView,LevelNewView,LevelEditView
from irrigator.views.envitem import EnvItemView,EnvItemsView,EnvItemNewView,EnvItemEditView,EnvItemDeleteView
from irrigator.views.history import HistoryView,HistorysView
from irrigator.views.log import LogView,LogsView
from irrigator.views.schedule import ScheduleView,SchedulesView,ScheduleNewView,ScheduleEditView,ScheduleDeleteView
from irrigator.views.group import GroupView,GroupsView,GroupNewView,GroupEditView,GroupDeleteView
from irrigator.views.dayrange import DayRangeView,DayRangesView,DayRangeNewView,DayRangeEditView,DayRangeDeleteView
from irrigator.views.dayrange import DayRangeView,DayRangesView,DayRangeNewView,DayRangeEditView,DayRangeDeleteView
from irrigator.views.day import DayView,DaysView,DayNewView,DayEditView,DayDeleteView
from irrigator.views.valveoverride import ValveOverrideView,ValveOverridesView,ValveOverrideNewView,ValveOverrideEditView,ValveOverrideDeleteView
from irrigator.views.groupoverride import GroupOverrideView,GroupOverridesView,GroupOverrideNewView,GroupOverrideEditView,GroupOverrideDeleteView

import irrigator.auth
import irrigator.views
import django.contrib.auth.views

urlpatterns = [
	url(r'^$', irrigator.views.home, name='home'),

	url(r'^site/$', SitesView.as_view()),
	url(r'^site/(?P<pk>\d+)$', SiteView.as_view()),
	url(r'^site/new$', SiteNewView.as_view()),
	url(r'^site/(?P<pk>\d+)/edit$', SiteEditView.as_view()),
	url(r'^site/(?P<pk>\d+)/delete$', SiteDeleteView.as_view()),

	url(r'^(?:site/(?P<site>\d+)/|)controller/$', ControllersView.as_view()),
	url(r'^controller/(?P<pk>\d+)$', ControllerView.as_view()),
	url(r'^controller/(?P<pk>\d+)/edit$', ControllerEditView.as_view()),
	url(r'^controller/(?P<pk>\d+)/delete$', ControllerDeleteView.as_view()),
	url(r'^site/(?P<site>\d+)/new/controller$', ControllerNewView.as_view()),

	url(r'^(?:site/(?P<site>\d+)/|)group/$', GroupsView.as_view()),
	url(r'^group/(?P<pk>\d+)$', GroupView.as_view()),
	url(r'^group/(?P<pk>\d+)/edit$', GroupEditView.as_view()),
	url(r'^group/(?P<pk>\d+)/delete$', GroupDeleteView.as_view()),
	url(r'^site/(?P<site>\d+)/new/group$', GroupNewView.as_view()),

	url(r'^(?:site/(?P<site>\d+)/|)feed/$', FeedsView.as_view()),
	url(r'^feed/(?P<pk>\d+)$', FeedView.as_view()),
	url(r'^feed/(?P<pk>\d+)/edit$', FeedEditView.as_view()),
	url(r'^feed/(?P<pk>\d+)/delete$', FeedDeleteView.as_view()),
	url(r'^site/(?P<site>\d+)/new/feed$', FeedNewView.as_view()),

	url(r'^valve/$', ValvesView.as_view()),
	url(r'^valve/(?P<pk>\d+)$', ValveView.as_view()),
	url(r'^valve/(?P<pk>\d+)/edit$', ValveEditView.as_view()),
	url(r'^valve/(?P<pk>\d+)/delete$', ValveDeleteView.as_view()),
	url(r'^(?:site/(?P<site>\d+)|feed/(?P<feed>\d+)|controller/(?P<controller>\d+)|envgroup/(?P<envgroup>\d+))/new/valve$', ValveNewView.as_view()),

	url(r'^(?:site/(?P<site>\d+)/|controller/(?P<controller>\d+)/|valve/(?P<valve>\d+)/|envgroup/(?P<envgroup>\d+)/|)level/$', LevelsView.as_view()),
	url(r'^level/(?P<pk>\d+)$', LevelView.as_view()),
	url(r'^level/(?P<pk>\d+)/edit$', LevelEditView.as_view()),
	url(r'^valve/(?P<valve>\d+)/new/level$', LevelNewView.as_view()),

	url(r'^(?:site/(?P<site>\d+)/|)envgroup/$', EnvGroupsView.as_view()),
	url(r'^envgroup/(?P<pk>\d+)$', EnvGroupView.as_view()),
	url(r'^envgroup/(?P<pk>\d+)/edit$', EnvGroupEditView.as_view()),
	url(r'^envgroup/(?P<pk>\d+)/delete$', EnvGroupDeleteView.as_view()),
	url(r'^site/(?P<site>\d+)/new/envgroup$', EnvGroupNewView.as_view()),

	url(r'^(?:envgroup/(?P<envgroup>\d+)/|)envitem/$', EnvItemsView.as_view()),
	url(r'^envitem/(?P<pk>\d+)$', EnvItemView.as_view()),
	url(r'^envitem/(?P<pk>\d+)/edit$', EnvItemEditView.as_view()),
	url(r'^envitem/(?P<pk>\d+)/delete$', EnvItemDeleteView.as_view()),
	url(r'^envgroup/(?P<envgroup>\d+)/new/envitem$', EnvItemNewView.as_view()),

	url(r'^(?:site/(?P<site>\d+)/|)history/$', HistorysView.as_view()),
	url(r'^history/(?P<pk>\d+)$', HistoryView.as_view()),

	url(r'^(?:site/(?P<site>\d+)/|controller/(?P<controller>\d+)/|valve/(?P<valve>\d+)/|envgroup/(?P<envgroup>\d+)/|)log/$', LogsView.as_view()),
	url(r'^(?:site/(?P<site>\d+)/|controller/(?P<controller>\d+)/|valve/(?P<valve>\d+)/|envgroup/(?P<envgroup>\d+)/|)log/(?P<pk>\d+)$', LogView.as_view()),

	url(r'^(?:site/(?P<site>\d+)/|controller/(?P<controller>\d+)/|feed/(?P<feed>\d+)/|envgroup/(?P<envgroup>\d+)/|valve/(?P<valve>\d+)/|)schedule/$', SchedulesView.as_view()),
	url(r'^(?:site/(?P<site>\d+)/|controller/(?P<controller>\d+)/|feed/(?P<feed>\d+)/|envgroup/(?P<envgroup>\d+)/|valve/(?P<valve>\d+)/|)new/schedule/$', ScheduleNewView.as_view()),
	url(r'^(?:site/(?P<site>\d+)/|controller/(?P<controller>\d+)/|feed/(?P<feed>\d+)/|envgroup/(?P<envgroup>\d+)/|valve/(?P<valve>\d+)/|)schedule/(?P<pk>\d+)$', ScheduleView.as_view()),
	url(r'^(?:site/(?P<site>\d+)/|controller/(?P<controller>\d+)/|feed/(?P<feed>\d+)/|envgroup/(?P<envgroup>\d+)/|valve/(?P<valve>\d+)/|)schedule/(?P<pk>\d+)/edit$', ScheduleEditView.as_view()),
	url(r'^(?:site/(?P<site>\d+)/|controller/(?P<controller>\d+)/|feed/(?P<feed>\d+)/|envgroup/(?P<envgroup>\d+)/|valve/(?P<valve>\d+)/|)schedule/(?P<pk>\d+)/delete$', ScheduleDeleteView.as_view()),

	url(r'^(?:valve/(?P<valve>\d+)|envgroup/(?P<envgroup>\d+)|feed/(?P<feed>\d+)|controller/(?P<controller>\d+)|site/(?P<site>\d+)|valve)/time$', ValveOverridesView.as_view()),
	url(r'^(?:valve/(?P<valve>\d+)|envgroup/(?P<envgroup>\d+)|feed/(?P<feed>\d+)|controller/(?P<controller>\d+)|site/(?P<site>\d+)|valve)/new/time$', ValveOverrideNewView.as_view()),
	url(r'^(?:valve/(?P<valve>\d+)|envgroup/(?P<envgroup>\d+)|feed/(?P<feed>\d+)|controller/(?P<controller>\d+)|site/(?P<site>\d+)|valve)/time/(?P<pk>\d+)$', ValveOverrideView.as_view()),
	url(r'^(?:valve/(?P<valve>\d+)|envgroup/(?P<envgroup>\d+)|feed/(?P<feed>\d+)|controller/(?P<controller>\d+)|site/(?P<site>\d+)|valve)/time/(?P<pk>\d+)/edit$', ValveOverrideEditView.as_view()),
	url(r'^(?:valve/(?P<valve>\d+)|envgroup/(?P<envgroup>\d+)|feed/(?P<feed>\d+)|controller/(?P<controller>\d+)|site/(?P<site>\d+)|valve)/time/(?P<pk>\d+)/delete$', ValveOverrideDeleteView.as_view()),

	# note that it's site/##/gtime, not time, as that's already used for valves
	url(r'^(?:group/(?P<group>\d+)/|site/(?P<site>\d+)/g|group/)time$', GroupOverridesView.as_view()),
	url(r'^(?:group/(?P<group>\d+)/|site/(?P<site>\d+)/g|group/)new/time$', GroupOverrideNewView.as_view()),
	url(r'^(?:group/(?P<group>\d+)/|site/(?P<site>\d+)/g|group/)time/(?P<pk>\d+)$', GroupOverrideView.as_view()),
	url(r'^(?:group/(?P<group>\d+)/|site/(?P<site>\d+)/g|group/)time/(?P<pk>\d+)/edit$', GroupOverrideEditView.as_view()),
	url(r'^(?:group/(?P<group>\d+)/|site/(?P<site>\d+)/g|group/)time/(?P<pk>\d+)/delete$', GroupOverrideDeleteView.as_view()),

	url(r'^dayrange/$', DayRangesView.as_view()),
	url(r'^dayrange/(?P<pk>\d+)$', DayRangeView.as_view()),
	url(r'^dayrange/new$', DayRangeNewView.as_view()),
	url(r'^dayrange/(?P<pk>\d+)/edit$', DayRangeEditView.as_view()),
	url(r'^dayrange/(?P<pk>\d+)/delete$', DayRangeDeleteView.as_view()),

	url(r'^day/$', DaysView.as_view()),
	url(r'^day/(?P<pk>\d+)$', DayView.as_view()),
	url(r'^day/new$', DayNewView.as_view()),
	url(r'^day/(?P<pk>\d+)/edit$', DayEditView.as_view()),
	url(r'^day/(?P<pk>\d+)/delete$', DayDeleteView.as_view()),

	# Login stuff
	url(r'^login/$', django.contrib.auth.views.login, {'template_name': 'auth/login.jinja'}),
	url(r'^login/logout$', django.contrib.auth.views.logout, {'template_name': 'auth/logout.jinja'}),
	url(r'^login/no_access$', irrigator.auth.no_access, {'template_name': 'auth/no_access.jinja'}),

	url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
	url(r'^admin/', include(admin.site.urls)),
]
