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
    'batt_stat', 'cell_stat', 'cell_op', 'v', 'v_boot', 'v_sys',
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

    datalogger_point = {
        'measurement': 'dataloggers',
        'tags': {
            'sn': datalogger_sn,
        },
        'fields': {
            'readings': len(decdata['sensors']),
            'uptime': decdata['time'] - decdata['boot'],
        },
        'time': decdata['time'],
    }
    if 'timestamp' in hologram_message:
        datalogger_point['fields']['delay'] = \
            int(hologram_message['timestamp']) - decdata['time']
    for tag in datalogger_tag_names:
        datalogger_point['tags'][tag] = decdata[tag]
    for field in datalogger_field_names:
        datalogger_point['fields'][field] = decdata[field]
    points.append(datalogger_point)

    influxdb_client.write_points(points, time_precision='s')


def sync_hologram_messages(datalogger_sn, limit=10000, timestart=0,
                           timeend=2147483647):
    hologram_device_id = get_hologram_device_id(datalogger_sn)
    messages = get_hologram_messages(
        deviceid=hologram_device_id, limit=limit, timestart=timestart,
        timeend=timeend,
    )
    for message in messages:
        try:
            write_data(message)
        except Exception as e:
            print(e)


def recalculate_data(datalogger_sn, seq, timestart=0, timeend=2147483647):
    sensor = Sensor.objects.get(datalogger__sn=datalogger_sn, seq=seq)
    query = """
        SELECT *
        FROM sensors
        WHERE
            dl_sn = '{datalogger_sn}' AND seq = '{seq:d}' AND
            client = '{client}' AND site = '{site}' AND label = '{label}' AND
            time >= {timestart:d}s AND time <= {timeend:d}s
    """.format(
        datalogger_sn=datalogger_sn, seq=seq,
        client=sensor.client, site=sensor.site, label=sensor.label,
        timestart=timestart, timeend=timeend,
    )
    old_points = influxdb_client.query(query, epoch='s').get_points()
    new_points = []
    for point in old_points:
        assert 'cal_m' in point
        point['cal_m'] = sensor.cal_m
        assert 'cal_b' in point
        point['cal_b'] = sensor.cal_b
        assert 'value' in point
        point['value'] = sensor.calculate(point['raw'])
        # Assume all strings are tags and all fields are floats.
        new_points.append({
            'measurement': 'sensors',
            'tags': {
                k: v for k, v in point.items()
                if isinstance(v, str)
            },
            'fields': {
                k: float(v) for k, v in point.items()
                if not isinstance(v, str) and k != 'time'
            },
            'time': point['time'],
        })
    influxdb_client.write_points(new_points, time_precision='s')
