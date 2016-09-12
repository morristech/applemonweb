#!/usr/bin/env python

import os
import sys

import django

curpath = os.path.dirname(__file__)
sys.path.append(os.path.join(curpath, '..'))

django.setup()

from armgmt.models import InvoiceLineAction


mapping = {'1': None, 'N/A': None}

actions = InvoiceLineAction.objects.all()
for old in actions:
    new_name = old.name.lower().rstrip('s')
    try:
        new_name = mapping[new_name]
    except KeyError:
        pass
    if old.name != new_name:
        if new_name:
            try:
                new = InvoiceLineAction.objects.get(name=new_name)
            except InvoiceLineAction.DoesNotExist:
                old.name = new_name
                old.save()
                continue
        else:
            new = None
        old.invoicelineitem_set.update(action=new)
        old.delete()
