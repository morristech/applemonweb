from django.conf.urls import url

from armgmt import views


urlpatterns = [
    # Redirect home page to admin site.
    url(r'^$', views.index, name='index'),
    # Render invoice at /invoice/YY-NUM.
    url(r'^invoice/([A-Z])N([0-9\-]+)', views.render_invoice, name='invoice'),
    # Render statement at /statement/CLIENT.
    url(r'^statement/(.*)', views.render_statement, name='statement'),
    # Provide autocomplete results for django-autocomplete-light.
    url(r'autocompletes/client/$', views.AutocompleteClient.as_view(),
        name='autocomplete-client'),
    url(r'autocompletes/invoice/$', views.AutocompleteInvoice.as_view(),
        name='autocomplete-invoice'),
    url(r'autocompletes/project/$', views.AutocompleteProject.as_view(),
        name='autocomplete-project'),
    url(r'autocompletes/invoiceno/$', views.AutocompleteInvoiceNo.as_view(),
        name='autocomplete-invoiceno'),
    url(r'autocompletes/projectno/$', views.AutocompleteProjectNo.as_view(),
        name='autocomplete-projectno'),
    # List report tools.
    url(r'^admin/tools/$', views.ToolsView.as_view(), name='tools'),
    # Create noise report from file upload.
    url(r'^admin/tools/noise/$', views.NoiseView.as_view(), name='noise'),
]
