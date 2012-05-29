from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from rainman import admin as rain_admin
from irrigator.views.site import SiteView,SitesView,SiteNewView,SiteEditView,SiteDeleteView
from irrigator.views.controller import ControllerView,ControllersView,ControllerNewView,ControllerEditView,ControllerDeleteView
from irrigator.views.feed import FeedView,FeedsView,FeedNewView,FeedEditView,FeedDeleteView
from irrigator.views.valve import ValveView,ValvesView,ValveNewView,ValveEditView,ValveDeleteView
from irrigator.views.paramgroup import ParamGroupView,ParamGroupsView,ParamGroupNewView,ParamGroupEditView,ParamGroupDeleteView

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
    url(r'^site/(?P<site>\d+)/new/controller$', ControllerNewView.as_view()),

    url(r'^feed/$', FeedsView.as_view()),
    url(r'^feed/(?P<pk>\d+)$', FeedView.as_view()),
    url(r'^feed/(?P<pk>\d+)/edit$', FeedEditView.as_view()),
    url(r'^feed/(?P<pk>\d+)/delete$', FeedDeleteView.as_view()),
    url(r'^site/(?P<site>\d+)/new/feed$', FeedNewView.as_view()),

    url(r'^valve/$', ValvesView.as_view()),
    url(r'^valve/(?P<pk>\d+)$', ValveView.as_view()),
    url(r'^valve/(?P<pk>\d+)/edit$', ValveEditView.as_view()),
    url(r'^valve/(?P<pk>\d+)/delete$', ValveDeleteView.as_view()),
    url(r'^site/(?P<site>\d+)/new/valve$', ValveNewView.as_view()),

	url(r'^params/$', ParamGroupsView.as_view()),
	url(r'^params/(?P<pk>\d+)$', ParamGroupView.as_view()),
	url(r'^params/(?P<pk>\d+)/edit$', ParamGroupEditView.as_view()),
	url(r'^params/(?P<pk>\d+)/delete$', ParamGroupDeleteView.as_view()),
	url(r'^site/(?P<site>\d+)/new/params$', ParamGroupNewView.as_view()),

	# Login stuff
	url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'auth/login.html'}),
	url(r'^login/logout$', 'django.contrib.auth.views.logout', {'template_name': 'auth/logout.html'}),
    url(r'^login/no_access$', 'irrigator.auth.no_access'),

    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
)
