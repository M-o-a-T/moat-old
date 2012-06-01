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

urlpatterns = patterns('',
	url(r'^$', 'irrigator.views.home', name='home'),

	url(r'^site/$', SitesView.as_view()),
	url(r'^site/(?P<pk>\d+)$', SiteView.as_view()),
	url(r'^site/new$', SiteNewView.as_view()),
	url(r'^site/(?P<pk>\d+)/edit$', SiteEditView.as_view()),
	url(r'^site/(?P<pk>\d+)/delete$', SiteDeleteView.as_view()),

	url(r'^controller/$', ControllersView.as_view()),
	url(r'^controller/(?P<pk>\d+)$', ControllerView.as_view()),
	url(r'^controller/(?P<pk>\d+)/edit$', ControllerEditView.as_view()),
	url(r'^controller/(?P<pk>\d+)/delete$', ControllerDeleteView.as_view()),
	url(r'^site/(?P<site>\d+)/controller$', ControllersView.as_view()),
	url(r'^site/(?P<site>\d+)/new/controller$', ControllerNewView.as_view()),

	url(r'^feed/$', FeedsView.as_view()),
	url(r'^feed/(?P<pk>\d+)$', FeedView.as_view()),
	url(r'^feed/(?P<pk>\d+)/edit$', FeedEditView.as_view()),
	url(r'^feed/(?P<pk>\d+)/delete$', FeedDeleteView.as_view()),
	url(r'^site/(?P<site>\d+)/feed$', FeedsView.as_view()),
	url(r'^site/(?P<site>\d+)/new/feed$', FeedNewView.as_view()),

	url(r'^valve/$', ValvesView.as_view()),
	url(r'^valve/(?P<pk>\d+)$', ValveView.as_view()),
	url(r'^valve/(?P<pk>\d+)/edit$', ValveEditView.as_view()),
	url(r'^valve/(?P<pk>\d+)/delete$', ValveDeleteView.as_view()),
	url(r'^site/(?P<site>\d+)/new/valve$', ValveNewView.as_view()),
	url(r'^feed/(?P<feed>\d+)/new/valve$', ValveNewView.as_view()),
	url(r'^controller/(?P<controller>\d+)/new/valve$', ValveNewView.as_view()),
	url(r'^envgroup/(?P<envgroup>\d+)/new/valve$', ValveNewView.as_view()),

	url(r'^level/$', LevelsView.as_view()),
	url(r'^level/(?P<pk>\d+)$', LevelView.as_view()),
	url(r'^level/(?P<pk>\d+)/edit$', LevelEditView.as_view()),
	url(r'^valve/(?P<valve>\d+)/level$', LevelsView.as_view()),
	url(r'^valve/(?P<valve>\d+)/new/level$', LevelNewView.as_view()),

	url(r'^envgroup/$', EnvGroupsView.as_view()),
	url(r'^envgroup/(?P<pk>\d+)$', EnvGroupView.as_view()),
	url(r'^envgroup/(?P<pk>\d+)/edit$', EnvGroupEditView.as_view()),
	url(r'^envgroup/(?P<pk>\d+)/delete$', EnvGroupDeleteView.as_view()),
	url(r'^site/(?P<site>\d+)/envgroup$', EnvGroupsView.as_view()),
	url(r'^site/(?P<site>\d+)/new/envgroup$', EnvGroupNewView.as_view()),

	url(r'^envitem/$', EnvItemsView.as_view()),
	url(r'^envitem/(?P<pk>\d+)$', EnvItemView.as_view()),
	url(r'^envitem/(?P<pk>\d+)/edit$', EnvItemEditView.as_view()),
	url(r'^envitem/(?P<pk>\d+)/delete$', EnvItemDeleteView.as_view()),
	url(r'^envgroup/(?P<envgroup>\d+)/envitem$', EnvItemsView.as_view()),
	url(r'^envgroup/(?P<envgroup>\d+)/new/envitem$', EnvItemNewView.as_view()),

	url(r'^history/$', HistorysView.as_view()),
	url(r'^history/(?P<pk>\d+)$', HistoryView.as_view()),
	url(r'^site/(?P<site>\d+)/history$', HistorysView.as_view()),

	url(r'^log/$', LogsView.as_view()),
	url(r'^log/(?P<pk>\d+)$', LogView.as_view()),
	url(r'^site/(?P<site>\d+)/log$', LogsView.as_view()),
	url(r'^site/(?P<site>\d+)/log/(?P<pk>\d+)$', LogView.as_view()),
	url(r'^controller/(?P<controller>\d+)/log$', LogsView.as_view()),
	url(r'^controller/(?P<controller>\d+)/log/(?P<pk>\d+)$', LogView.as_view()),
	url(r'^valve/(?P<valve>\d+)/log$', LogsView.as_view()),
	url(r'^valve/(?P<valve>\d+)/log/(?P<pk>\d+)$', LogView.as_view()),
	url(r'^envgroup/(?P<envgroup>\d+)/log$', LogsView.as_view()),
	url(r'^envgroup/(?P<envgroup>\d+)/log/(?P<pk>\d+)$', LogView.as_view()),

	url(r'^schedule/$', SchedulesView.as_view()),
	url(r'^schedule/(?P<pk>\d+)$', ScheduleView.as_view()),
	url(r'^schedule/(?P<pk>\d+)/edit$', ScheduleEditView.as_view()),
	url(r'^schedule/(?P<pk>\d+)/delete$', ScheduleDeleteView.as_view()),
	url(r'^site/(?P<site>\d+)/schedule$', SchedulesView.as_view()),
	url(r'^site/(?P<site>\d+)/new/schedule$', ScheduleNewView.as_view()),
	url(r'^site/(?P<site>\d+)/schedule/(?P<pk>\d+)$', ScheduleView.as_view()),
	url(r'^site/(?P<site>\d+)/schedule/(?P<pk>\d+)/edit$', ScheduleEditView.as_view()),
	url(r'^site/(?P<site>\d+)/schedule/(?P<pk>\d+)/delete$', ScheduleDeleteView.as_view()),
	url(r'^controller/(?P<controller>\d+)/schedule$', SchedulesView.as_view()),
	url(r'^controller/(?P<controller>\d+)/new/schedule$', ScheduleNewView.as_view()),
	url(r'^controller/(?P<controller>\d+)/schedule/(?P<pk>\d+)$', ScheduleView.as_view()),
	url(r'^controller/(?P<controller>\d+)/schedule/(?P<pk>\d+)/edit$', ScheduleEditView.as_view()),
	url(r'^controller/(?P<controller>\d+)/schedule/(?P<pk>\d+)/delete$', ScheduleDeleteView.as_view()),
	url(r'^feed/(?P<feed>\d+)/schedule$', SchedulesView.as_view()),
	url(r'^feed/(?P<feed>\d+)/new/schedule$', ScheduleNewView.as_view()),
	url(r'^feed/(?P<feed>\d+)/schedule/(?P<pk>\d+)$', ScheduleView.as_view()),
	url(r'^feed/(?P<feed>\d+)/schedule/(?P<pk>\d+)/edit$', ScheduleEditView.as_view()),
	url(r'^feed/(?P<feed>\d+)/schedule/(?P<pk>\d+)/delete$', ScheduleDeleteView.as_view()),
	url(r'^envgroup/(?P<envgroup>\d+)/schedule$', SchedulesView.as_view()),
	url(r'^envgroup/(?P<envgroup>\d+)/new/schedule$', ScheduleNewView.as_view()),
	url(r'^envgroup/(?P<envgroup>\d+)/schedule/(?P<pk>\d+)$', ScheduleView.as_view()),
	url(r'^envgroup/(?P<envgroup>\d+)/schedule/(?P<pk>\d+)/edit$', ScheduleEditView.as_view()),
	url(r'^envgroup/(?P<envgroup>\d+)/schedule/(?P<pk>\d+)/delete$', ScheduleDeleteView.as_view()),
	url(r'^valve/(?P<valve>\d+)/schedule$', SchedulesView.as_view()),
	url(r'^valve/(?P<valve>\d+)/new/schedule$', ScheduleNewView.as_view()),
	url(r'^valve/(?P<valve>\d+)/schedule/(?P<pk>\d+)$', ScheduleView.as_view()),
	url(r'^valve/(?P<valve>\d+)/schedule/(?P<pk>\d+)/edit$', ScheduleEditView.as_view()),
	url(r'^valve/(?P<valve>\d+)/schedule/(?P<pk>\d+)/delete$', ScheduleDeleteView.as_view()),

	# Login stuff
	url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'auth/login.html'}),
	url(r'^login/logout$', 'django.contrib.auth.views.logout', {'template_name': 'auth/logout.html'}),
	url(r'^login/no_access$', 'irrigator.auth.no_access'),

	url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
	url(r'^admin/', include(admin.site.urls)),
)
