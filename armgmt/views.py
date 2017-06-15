from datetime import date
from decimal import Decimal
import os
from urllib.parse import quote

from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from formtools.wizard.views import SessionWizardView

from armgmt.forms import InvoiceForm1, InvoiceForm2, ToolForm
from armgmt.models import Client, DocumentNo, Invoice
from armgmt.tex import pdflatex
from armgmt.tools.noise import generate_noise_report


logo_path = os.path.join(os.getcwd(), 'armgmt/templates/armgmt/logo')


def pdf_response(pdf, filename):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(
        quote(filename)
    )
    response['Content-Length'] = len(pdf)
    response.write(pdf)
    return response


def render_latex(request, template, dictionary, filename):
    latex = render_to_string(template, dictionary)
    pdf = pdflatex(latex)
    return pdf_response(pdf, filename)


def index(request):
    """Redirect home page to admin site."""
    return HttpResponseRedirect(reverse('admin:index'))


@login_required
def render_invoice(request, invoice_no):
    try:
        invoice = Invoice.objects.select_related().get(
            no=DocumentNo(invoice_no)
        )
        line_items = (invoice.invoicelineitem_set.select_related('action')
                      .order_by('position', 'date')
                      .all())
    except (ValueError, Invoice.DoesNotExist):
        raise Http404("Invoice %s not found." % invoice_no)
    dictionary = {'invoice': invoice,
                  'line_items': line_items,
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
                          if e['age'] > 30) - balances['over90'] -
                          balances['over60'])
    balances['under30'] = (balances['total'] -
                           balances['over90'] - balances['over60'] -
                           balances['over30'])

    context = {'date': today,
               'client': client,
               'entries': entries,
               'balances': balances,
               'logo_path': logo_path}
    filename = 'statement-%s.pdf' % client.name.lower()
    return render_latex(request, 'armgmt/statement.tex', context, filename)


class ToolsView(LoginRequiredMixin, TemplateView):
    """List available report tools."""

    template_name = 'armgmt/tools.html'

    def get_context_data(self, **kwargs):
        context = super(ToolsView, self).get_context_data(**kwargs)
        context['title'] = "Tools"
        context['tool_views'] = [NoiseView]
        return context


class BaseToolView(LoginRequiredMixin, FormView):
    """Render generic report from data in file upload."""

    form_class = ToolForm
    template_name = 'armgmt/tool.html'
    title = ""
    description = ""
    url = None

    def get_context_data(self, **kwargs):
        context = super(BaseToolView, self).get_context_data(**kwargs)
        context['title'] = self.title
        context['description'] = self.description
        return context

    def handler(self, files):
        raise NotImplementedError

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            files = request.FILES.getlist('files')
            try:
                (pdf, filename) = self.handler(files)
            except AssertionError as e:
                form.add_error(None, e)
                return self.form_invalid(form)
            return pdf_response(pdf, filename)
        else:
            return self.form_invalid(form)


class NoiseView(BaseToolView):
    """Render noise report from data in file upload."""

    title = "Noise Monitoring Report"
    description = "Upload files to generate a noise monitoring report."
    url = reverse_lazy('noise')

    def handler(self, files):
        return generate_noise_report(files)


class InvoiceWizard(LoginRequiredMixin, SessionWizardView):
    """Create invoice from wizard."""

    form_list = [InvoiceForm1, InvoiceForm2]
    template_name = 'armgmt/invoice-wizard.html'

    def get_form_kwargs(self, step=None):
        if step == '1':
            return {'client': self.get_cleaned_data_for_step('0')['client']}
        return {}

    def get_context_data(self, form, **kwargs):
        context = super(InvoiceWizard, self).get_context_data(form=form,
                                                              **kwargs)
        context['title'] = "Invoice Wizard"
        context['site_title'] = admin.AdminSite.site_title
        context['site_header'] = admin.AdminSite.site_header
        return context

    def done(self, form_list, **kwargs):
        data = self.get_all_cleaned_data()
        invoice = Invoice(**data)
        invoice.clean()
        invoice.save()
        return HttpResponseRedirect(
            reverse('admin:armgmt_invoice_change', args=(invoice.id,)))
