from django.conf.urls import url

from armgmt import views


urlpatterns = [
    # Redirect home page to admin site.
    url(r'^$', views.index, name='index'),
    # Render invoice at /invoice/YY-NUM.
    url(r'^invoice/([0-9\-]+)', views.render_invoice, name='invoice'),
    # Render statement at /statement/CLIENT.
    url(r'^statement/(.*)', views.render_statement, name='statement'),
    # List report tools.
    url(r'^admin/tools/$', views.ToolsView.as_view(), name='tools'),
    # Create noise report from file upload.
    url(r'^admin/tools/noise/$', views.NoiseView.as_view(), name='noise'),
]
