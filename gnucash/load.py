#!/usr/bin/env python

import csv
import re
import os
import sys
from datetime import datetime
from decimal import Decimal

import django

curpath = os.path.dirname(__file__)
sys.path.append(os.path.join(curpath, '..'))
sys.path.append('.')

django.setup()

from gcinvoice import Gcinvoice
from armgmt.models import (Client, DocumentNo, Project, Invoice,
                           InvoiceLineItem, InvoiceLineAction, Payment)

gcfile = 'accounting.gnucash'
infile = 'payments.csv'


def str2date(text):
    year = int(text.split('/')[2])
    if year > 99:
        date = datetime.strptime(text.strip(), '%m/%d/%Y').date()
    else:
        date = datetime.strptime(text.strip(), '%m/%d/%y').date()
    return date


gc = Gcinvoice()
gc.parse(gcfile)

for obj in [Client, Project, Invoice, InvoiceLineItem, InvoiceLineAction,
            Payment]:
    obj.objects.all().delete()

for customer in gc.customers.values():
    if customer['full_name'] == "DELETEME":
        continue
    name = customer['name'].strip()
    if Client.objects.filter(name=name):
        print("Error adding client: duplicate client name: %s" % name)
        continue
    contact_name = customer['full_name']
    if len(customer['address']) == 2:
        print("Error adding client: no firm name for {}".format(name))
        customer['address'].insert(0, '')
    elif len(customer['address']) == 4:
        print("Error adding client: dropping address line {} ({})".format(
              customer['address'][0], name))
        del customer['address'][0]
    assert len(customer['address']) == 3
    firm_name = customer['address'][0]
    address2 = customer['address'][1]
    if ',' in customer['address'][2]:
        (city, notcity) = customer['address'][2].split(',')
        (state, zip_code) = notcity.strip().split()
    else:
        last_line = customer['address'][2].split()
        city = ' '.join(last_line[:-2])
        state = last_line[-2]
        zip_code = last_line[-1]
    c = Client(name=name, contact_name=contact_name, firm_name=firm_name,
               address2=address2, city=city, state=state, zip_code=zip_code)
    #c.clean()
    c.save()

for job in gc.jobs.values():
    if job['name'] == "DELETEME":
        continue
    try:
        no = DocumentNo(job['id'])
    except Exception as e:
        print("Error adding project: unable to parse project no. %s: %s" %
          (job['id'], e))
        continue
    if Project.objects.filter(no=no):
        print("Error adding project: duplicate project no. %s" % str(no))
        continue
    client = Client.objects.get(name=job['owner']['name'].strip())
    numbers = [int(n) for n in job['id'].split('-')]
    year = 2000 + numbers[0]
    #num = numbers[1]
    assert year <= 2016 and year > 2005, "%s %s" % (job['id'], year)
    date = datetime(year, 1, 1).date()
    name = re.match('([ -]{0,1}\w+){0,12}',
            " ".join(job['name'].split()).strip()).group()
    notes = "\n".join([n.strip() for n in job['name'].split('\\\\')])
    p = Project(client=client, start_date=date, no=no, name=name,
                content=notes)
    p.clean()
    p.save()

for invc in gc.invoices.values():
    if invc['notes'] == "DELETEME":
        continue
    if invc['date_posted']:
        no = DocumentNo(invc['id'])
        try:
            no = DocumentNo(invc['id'])
        except Exception as e:
            print("Error adding invoice: unable to parse invoice no. %s: %s" %
              (invc['id'], e))
            continue
        if Invoice.objects.filter(no=no):
            print("Error adding invoice: duplicate invoice no. %s" % str(no))
            continue
        client = Client.objects.get(name=invc['owner']['name'].strip())
        date = invc['date_posted']
        #num = int(invc['id'].split('-')[1])
        if invc['notes']:
            notes = "\n".join([n.strip() for n in invc['notes'].split('\\\\')])
        else:
            notes = ""
        #job_numbers = [int(n) for n in invc['job']['id'].split('-')]
        #job_year = 2000 + job_numbers[0]
        #job_num = job_numbers[1]
        try:
            project_no = DocumentNo(invc['job']['id'])
        except Exception as e:
            print("Error adding invoice: unable to parse project no. %s on invoice no. %s: %s" %
                  (invc['job']['id'], invc['id'], e))
            continue
        project = Project.objects.get(no=project_no)
        name = project.name
        i = Invoice(client=client, date=date, no=no, content=notes,
                    name=name, project=project)
        try:
            i.clean()
        except Exception as e:
            print("Error adding invoice: error validating invoice no. %s with project %s and client %s: %s" %
                  (str(no), project, client, e))
        i.save()
        position = 0
        for e in invc['entries']:
            if e['action']:
                qset = InvoiceLineAction.objects.filter(name=e['action'].strip())
                if qset:
                    action = qset[0]
                else:
                    action = InvoiceLineAction(name=e['action'].strip())
                    action.clean()
                    action.save()
            else:
                action = None
            date = e['date']
            if e['description']:
                description = e['description']
            else:
                description = ''
            qty = e['qty']
            unit_price = e['price']
            l = InvoiceLineItem(invoice=i, date=date,
                                content=description, qty=qty,
                                action=action, unit_price=unit_price,
                                position=position)
            l.clean()
            l.save()
            position += 1

with open(infile, 'r') as f:
    reader = csv.reader(f)
    for row in reader:
        number = row[0].strip().lower()
        if not (number.startswith('invoice') or number.startswith('no')):
            #numbers = [int(n) for n in number.split('-')]
            #year = 2000 + numbers[0]
            #num = numbers[1]
            no = DocumentNo(number)
            try:
                invoice = Invoice.objects.get(no=no)
            except Exception as e:
                print("Error adding payment: unable to find invoice no. %s: %s" %
                      (str(no), e))
                continue
            for n in range(1, len(row), 2):
                if row[n]:
                    date = str2date(row[n])
                    amount = Decimal(row[n+1].strip().strip('$,'))
                else:
                    break
                p = Payment(invoice=invoice, date=date, amount=amount,
                            notes="")
                p.clean()
                p.save()
