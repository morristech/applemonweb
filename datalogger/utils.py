from base64 import b64decode
import json

from influxdb import InfluxDBClient

from datalogger.models import Sensor
from datalogger.hologram_api import (get_hologram_device_id,
                                     get_hologram_messages)


influxdb_client = InfluxDBClient(database='sensordata')
datalogger_field_names = [
    'batt_mv', 'batt_pct', 'boot', 'cell_rssi', 'rh', 'temp',
]
datalogger_tag_names = [
    'batt_stat', 'cell_stat', 'cell_op', 'v',
]


def decode_hologram_data(data):
    return json.loads(b64decode(data).decode())


def write_data(hologram_message):
    points = []
    datalogger_sn = hologram_message['device_name']
    decdata = decode_hologram_data(hologram_message['data'])

    seq = 0
    for (epoch, raw, raw_sd) in decdata['sensors']:
        sensor = Sensor.objects.get(datalogger__sn=datalogger_sn, seq=seq)
        points.append({
            'measurement': 'sensors',
            'tags': {
                'dl_sn': datalogger_sn,
                'seq': seq,
                'client': sensor.client,
                'site': sensor.site,
                'label': sensor.label,
            },
            'fields': {
                'raw': raw,
                'raw_sd': raw_sd,
                'cal_m': sensor.cal_m,
                'cal_b': sensor.cal_b,
                'value': sensor.calculate(raw),
            },
            'time': epoch,
        })
        seq += 1

    datalogger_point = {
        'measurement': 'dataloggers',
        'tags': {
            'sn': datalogger_sn,
        },
        'fields': {
            'delay': int(hologram_message['timestamp']) - decdata['time'],
        },
        'time': decdata['time'],
    }
    for tag in datalogger_tag_names:
        datalogger_point['tags'][tag] = decdata[tag]
    for field in datalogger_field_names:
        datalogger_point['fields'][field] = decdata[field]
    points.append(datalogger_point)

    influxdb_client.write_points(points, time_precision='s')


def sync_hologram_messages(datalogger_sn, limit=100, timestart=0):
    hologram_device_id = get_hologram_device_id(datalogger_sn)
    messages = get_hologram_messages(
        deviceid=hologram_device_id, limit=limit, timestart=timestart,
    )
    for message in messages:
        try:
            write_data(message)
        except Exception as e:
            print(e)
