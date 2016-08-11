#!/usr/bin/env python

import os
import sys

import django

curpath = os.path.dirname(__file__)
sys.path.append(os.path.join(curpath, '..'))

django.setup()

from armgmt.models import InvoiceLineAction


mapping = {'1':        None,
           'Balance':  'balance',
           'days':     'day',
           'Day':      'day',
           'Days':     'day',
           'fees':     'fee',
           'Hours':    'hours',
           'N/A':      None,
           'Service':  'service',
           'services': 'service',
           'Services': 'service',
           'sets':     'set',
           'Set':      'set',
           'Sets':     'set',
           'Visit':    'visit',
           'visits':   'visit'}


for old_name, new_name in mapping.items():
    try:
        old = InvoiceLineAction.objects.get(name=old_name)
    except InvoiceLineAction.DoesNotExist:
        continue
    if new_name:
        new = InvoiceLineAction.objects.get(name=new_name)
    else:
        new = None
    old.invoicelineitem_set.update(action=new)
    old.delete()
