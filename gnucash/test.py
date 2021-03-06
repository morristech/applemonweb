#!/usr/bin/env python

import os
import sys
from urllib.parse import unquote

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
    filename = unquote(r['Content-Disposition'].split("filename*=utf-8''")[1])
    path = os.path.join(output_dir, filename)
    with open(path, 'wb') as f:
        f.write(r.content)

for invoice in invoices:
    print("Rendering Invoice no. %s" % invoice.code)
    r = render_invoice(request, invoice.biller.code, invoice.no)
    filename = str(r['Content-Disposition'].split("utf-8''")[1])
    path = os.path.join(output_dir, filename)
    with open(path, 'wb') as f:
        f.write(r.content)
