from django.conf.urls import include, url
from django.contrib import admin
from django.urls import path


urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^admin/', include('massadmin.urls')),
    url(r'^explorer/', include('explorer.urls')),
    url(r'^', include('armgmt.urls'), name='armgmt'),
]
