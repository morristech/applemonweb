import json
from urllib.parse import parse_qs

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from datalogger.utils import write_data


@method_decorator(csrf_exempt, name='dispatch')
class HologramWebhook(View):

    key = settings.SECRETS['HOLOGRAM_SHARED_SECRET']

    def post(self, request, *args, **kwargs):
        data = parse_qs(request.body.decode())
        assert len(data['key']) == 1
        if data['key'][0] != self.key:
            raise PermissionDenied
        assert len(data['payload']) == 1
        hologram_message = json.loads(data['payload'][0])
        write_data(hologram_message)
        return HttpResponse("OK")
