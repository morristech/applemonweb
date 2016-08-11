#!/usr/bin/env python

import os
import sys

import django

curpath = os.path.dirname(__file__)
sys.path.append(os.path.join(curpath, '..'))

django.setup()

from armgmt.models import Client, Invoice
from armgmt.views import render_statement, render_invoice


output_dir = 'output'
clients = Client.objects.all()
invoices = Invoice.objects.all()


class DummyObject(object):
    """Work around required authentication with dummy request object."""
    pass
request = DummyObject()
request.user = DummyObject()
request.user.is_authenticated = lambda: True

for client in clients:
    print("Rendering statement for client %s" % client.name)
    r = render_statement(request, client.name)
    filename = r['Content-Disposition'].split('=')[1]
    path = os.path.join(output_dir, filename)
    with open(path, 'wb') as f:
        f.write(r.content)

for invoice in invoices:
    print("Rendering Invoice no. %s" % str(invoice.no))
    r = render_invoice(request, invoice.no)
    filename = r['Content-Disposition'].split('=')[1]
    path = os.path.join(output_dir, filename)
    with open(path, 'wb') as f:
        f.write(r.content)
