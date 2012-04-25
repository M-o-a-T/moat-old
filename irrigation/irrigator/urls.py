from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from rainman import admin as rain_admin

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'regner.views.home', name='home'),
    # url(r'^regner/', include('regner.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
