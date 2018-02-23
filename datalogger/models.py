from django.core.exceptions import ValidationError
from django.db import models

from datalogger.hologram_api import (get_hologram_device_id,
                                     get_hologram_device_url)


class Datalogger(models.Model):
    """Datalogger configuration"""
    sn = models.SlugField()
    hologram_id = models.SlugField()

    def get_absolute_url(self):
        return get_hologram_device_url(self.hologram_id)

    def clean(self):
        try:
            self.sn = int(self.sn)
            if self.sn < 0:
                raise ValueError
        except ValueError:
            raise ValidationError(
                "Datalogger serial number must be a positive integer."
            )
        self.hologram_id = get_hologram_device_id(self.sn)

    def __str__(self):
        return str(self.sn)


class Sensor(models.Model):
    """Sensor data configuration"""
    client = models.SlugField()
    site = models.SlugField()
    label = models.SlugField()
    cal_m = models.FloatField(null=True, blank=True)
    cal_b = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True)
    datalogger = models.ForeignKey(Datalogger, on_delete=models.CASCADE)
    seq = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def name(self):
        return "{}-{}-{}".format(self.client, self.site, self.label)

    def calculate(self, raw):
        if self.cal_m is None or self.cal_b is None:
            return None
        return self.cal_m * raw + self.cal_b

    def clean(self):
        if self.seq is None:
            seq_max = Sensor.objects.filter(
                datalogger=self.datalogger
            ).aggregate(models.Max('seq'))['seq__max']
            if seq_max is None:
                seq_max = -1
            self.seq = seq_max + 1

    def __str__(self):
        return self.name()

    class Meta:
        ordering = ['client', 'site', 'label']
        unique_together = (
            ('client', 'site', 'label'),
            ('datalogger', 'seq'),
        )
