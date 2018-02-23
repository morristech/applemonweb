import json
from urllib.parse import urljoin

from django.conf import settings
import requests

hologram_base_url = 'https://dashboard.hologram.io/'
hologram_api_base_url = urljoin(hologram_base_url, 'api/1/')
hologram_api_key = settings.SECRETS['HOLOGRAM_API_KEY']


def get_hologram_device_id(datalogger_sn):
    """Convert datalogger serial number to Hologram device ID."""
    url = urljoin(hologram_api_base_url, 'devices')
    payload = {
        'apikey': hologram_api_key,
        'name': datalogger_sn,
    }
    r = requests.get(url, params=payload)
    data = r.json()['data']
    assert len(data) == 1
    return data[0]['id']


def get_hologram_device_url(hologram_device_id):
    """Return Hologram Dashboard device URL."""
    return urljoin(
        hologram_base_url,
        'device/{}/message/inbound'.format(int(hologram_device_id)),
    )


def get_hologram_messages(**kwargs):
    """Fetch Hologram Cloud messages."""
    url = urljoin(hologram_api_base_url, 'csr/rdm')
    payload = {'apikey': hologram_api_key}
    payload.update(kwargs)
    r = requests.get(url, params=payload)
    data = r.json()['data']
    return [json.loads(message['data']) for message in data]
