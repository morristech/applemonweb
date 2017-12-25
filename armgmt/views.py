from datetime import date
from decimal import Decimal
import os
from urllib.parse import quote

from dal.autocomplete import Select2QuerySetView
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView
from django.views.generic.edit import FormView

from armgmt.forms import ToolForm
from armgmt.models import Client, DocumentNo, Invoice, Project
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


class AutocompleteBase(LoginRequiredMixin, Select2QuerySetView):
    """Provide generic autocomplete results for form widget."""

    qs = None

    def get_queryset(self):
        items = {k: v for k, v in self.forwarded.items() if v}
        return self.qs.filter(**items)


class AutocompleteClient(AutocompleteBase):
    qs = Client.objects.filter(active=True)


class AutocompleteInvoice(AutocompleteBase):
    qs = Invoice.objects.all()


class AutocompleteProject(AutocompleteBase):
    qs = Project.objects.all()
