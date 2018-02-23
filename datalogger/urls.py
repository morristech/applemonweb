from django.conf.urls import url

from datalogger import views


urlpatterns = [
    url(r'^api/hologram/webhook/$', views.HologramWebhook.as_view(),
        name='hologram_webhook'),
]
