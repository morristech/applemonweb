from django.conf.urls import include, url
from django.contrib import admin
from django.http import HttpResponseServerError
from django.template import loader
from django.urls import path


urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^admin/', include('massadmin.urls')),
    url(r'^explorer/', include('explorer.urls')),
    url(r'^', include('armgmt.urls'), name='armgmt'),
    url(r'^', include('datalogger.urls'), name='datalogger'),
]


def handler500(request):
    """500 error handler which includes ``request`` in the context."""
    try:
        template = loader.get_template('500.html')
        body = template.render(request=request)
        return HttpResponseServerError(body)
    except Exception:
        return HttpResponseServerError('500 Internal Server Error')
