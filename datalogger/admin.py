from django.contrib import admin

from datalogger.models import Datalogger, Sensor


@admin.register(Datalogger)
class DataloggerAdmin(admin.ModelAdmin):
    list_display = ['sn', 'hologram_id']
    list_display_links = ['sn']
    readonly_fields = ['hologram_id']
    search_fields = [
        'sn', 'hologram_id',
        'sensor__client', 'sensor__site', 'sensor__label',
    ]


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    date_hierarchy = 'updated_at'
    list_display = ['name', 'cal_m', 'cal_b', 'datalogger', 'seq']
    list_display_links = ['name']
    list_filter = ['client', 'site']
    readonly_fields = ['seq', 'created_at', 'updated_at']
    search_fields = ['client', 'site', 'label', 'notes', 'datalogger__sn']
