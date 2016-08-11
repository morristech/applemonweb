from datetime import date
from decimal import Decimal
import os

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.utils.decorators import method_decorator
from formtools.wizard.views import SessionWizardView

from armgmt.forms import InvoiceForm1, InvoiceForm2
from armgmt.models import Client, DocumentNo, Invoice
from armgmt.tex import render_latex


logo_path = os.path.join(os.getcwd(), 'armgmt/templates/armgmt/logo')


def index(request):
    """Redirect home page to admin site."""
    return HttpResponseRedirect(reverse('admin:index'))


@login_required
def render_invoice(request, invoice_no):
    try:
        invoice = Invoice.objects.select_related().get(
            no=DocumentNo(invoice_no)
        )
        services = invoice.service_set.select_related('action').order_by(
                   'position', 'date').all()
    except (ValueError, Invoice.DoesNotExist):
        raise Http404("Invoice %s not found." % invoice_no)
    dictionary = {'invoice': invoice,
                  'services': services,
                  'logo_path': logo_path}
    filename = 'invoice-%s.pdf' % str(invoice.no)
    return render_latex(request, 'armgmt/invoice.tex', dictionary, filename)


@login_required
def render_statement(request, client_name):
    dateformat = '%m/%d/%y'
    try:
        client = Client.objects.get(name=client_name)
    except Client.DoesNotExist:
        raise Http404("Client %s not found." % client_name)
    today = date.today()
    running_balance = Decimal(0)

    entries = []
    invoice_set = client.invoice_set.prefetch_related('payment_set').all()
    for invoice in invoice_set.order_by('no'):
        if invoice.balance:
            e = {}
            for attr in ['no', 'amount', 'name', 'balance']:
                e[attr] = getattr(invoice, attr)
            e['date'] = invoice.date.strftime(dateformat)
            e['age'] = (today - invoice.date).days
            running_balance += invoice.balance
            e['running_balance'] = running_balance
            payments = invoice.payment_set.all()
            if payments:
                e['rows'] = len(payments)
                e['payments'] = []
                for payment in payments:
                    e['payments'].append((payment.date.strftime(dateformat),
                                          payment.amount))
            else:
                e['rows'] = 1
                e['payments'] = []
            entries.append(e)

    balances = {}
    balances['total'] = client.owed()
    assert balances['total'] == running_balance, \
        "Total balance %s must equal last running balance %s" % (
            client.owed(),
            running_balance,
         )
    balances['over90'] = (sum(e['balance'] for e in entries
                          if e['age'] > 90))
    balances['over60'] = (sum(e['balance'] for e in entries
                          if e['age'] > 60) - balances['over90'])
    balances['over30'] = (sum(e['balance'] for e in entries
                          if e['age'] > 30) - balances['over90']
                          - balances['over60'])
    balances['under30'] = (balances['total']
                           - balances['over90'] - balances['over60']
                           - balances['over30'])

    context = {'date': today,
               'client': client,
               'entries': entries,
               'balances': balances,
               'logo_path': logo_path}
    filename = 'statement-%s.pdf' % client.name.lower()
    return render_latex(request, 'armgmt/statement.tex', context, filename)


class InvoiceWizard(SessionWizardView):
    """Create invoice from wizard."""

    form_list = [InvoiceForm1, InvoiceForm2]
    template_name = 'armgmt/invoice-wizard.html'

    def get_form_kwargs(self, step):
        if step == '1':
            return {'client': self.get_cleaned_data_for_step('0')['client']}
        return {}

    def done(self, form_list, form_dict, **kwargs):
        data = self.get_all_cleaned_data()
        invoice = Invoice(**data)
        invoice.clean()
        invoice.save()
        return HttpResponseRedirect(
            reverse('admin:armgmt_invoice_change', args=(invoice.id,)))

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(InvoiceWizard, self).dispatch(*args, **kwargs)
