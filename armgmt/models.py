from datetime import date
from decimal import Decimal
from numbers import Number

from django import forms
from django.db import models
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse


def agg_total(qset):
    """Sum amounts in a QuerySet of invoice line items or payments."""
    if qset.model is InvoiceLineItem:
        agg = models.Sum(models.F('qty') * models.F('unit_price'))
    elif qset.model is Payment:
        agg = models.Sum('amount')
    total = qset.aggregate(total=agg)['total']
    if total:
        return total.quantize(Decimal('.01'))
    else:
        return 0


def str2num(s, format=tuple):
    """Parse year and number from string of form yynum or yy-num."""
    s = str(s).strip()
    if len(s) == 0:
        return None
    elif len(s) == 5:
        # Assume string is of form 'yynum'.
        yy = int(s[:2])
        num = int(s[2:])
    elif len(s) == 6 and s[2] == '-':
        # Assume string is of form 'yy-num'.
        yy = int(s[:2])
        num = int(s[3:])
    else:
        raise ValueError("Could not parse '%s' as yy-num." % s)
    if format == tuple:
        # Format year and number as a tuple.
        return (yy, num)
    else:
        # Format based on a number of form yynum.
        return format(yy * 1000 + num)


class DocumentNo(tuple):
    __slots__ = []

    def __new__(cls, value):
        if value is None:
            return None
        elif type(value) is DocumentNo:
            return value
        elif isinstance(value, tuple):
            # Assume tuple is of form (yy, num).
            yy = int(value[0])
            num = int(value[1])
        elif isinstance(value, Number) and value >= 0 and value < 100000:
            # Assume number is of form yynum.
            yy = int(value / 1000)
            num = int(value - yy * 1000)
        else:
            yy, num = str2num(value)
        if yy < 0 or yy > 99:
            raise ValueError("Invalid document year prefix: %s." % yy)
        if num < 101 or num > 999:
            raise ValueError("Invalid document number suffix: %s." % num)
        return tuple.__new__(cls, (yy, num))

    def __int__(self):
        """Convert self to integer of form yynum."""
        return int(self[0] * 1000 + self[1])

    def __add__(self, other):
        """Add another number to document number suffix (num)."""
        return DocumentNo((self[0], self[1] + other))
    __radd__ = __add__

    def __sub__(self, other):
        """Subtract another number from document number suffix (num)."""
        return DocumentNo((self[0], self[1] - other))

    def __str__(self):
        """Print self as form yy-num."""
        return '%02d-%03d' % (self[0], self[1])

    def __repr__(self):
        """Represent self as form DocumentNo((yy, num))."""
        return 'DocumentNo((%s, %s))' % (self[0], self[1])


def validate_DocumentNo(value, output=False):
    """Validate DocumentNo by checking for ValueError."""
    try:
        d = DocumentNo(value)
    except ValueError as e:
        raise ValidationError(e)
    if output:
        return d


class DocumentNoField(models.Field):
    """Custom Django model field with yy-num DocumentNo object."""
    description = "Document number of form yy-num"

    def __init__(self, *args, **kwargs):
        if 'validators' not in kwargs:
            kwargs['validators'] = []
        if validate_DocumentNo not in kwargs['validators']:
            kwargs['validators'].append(validate_DocumentNo)
        super(DocumentNoField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'IntegerField'

    def to_python(self, value):
        return validate_DocumentNo(value, output=True)

    def from_db_value(self, value, expression, connection, context):
        return str(self.to_python(value))

    def get_prep_value(self, value):
        return int(self.to_python(value))

    def formfield(self, **kwargs):
        if 'validators' not in kwargs:
            kwargs['validators'] = []
        if validate_DocumentNo not in kwargs['validators']:
            kwargs['validators'].append(validate_DocumentNo)
        kwargs['form_class'] = forms.CharField
        kwargs['max_length'] = 6
        return super(DocumentNoField, self).formfield(**kwargs)


class Client(models.Model):
    name = models.CharField(unique=True, max_length=127)
    address = models.TextField()
    notes = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    def billed(self):
        invoice_set = InvoiceLineItem.objects.filter(invoice__client=self)
        return agg_total(invoice_set)

    def paid(self):
        payment_set = Payment.objects.filter(invoice__client=self)
        invoice_set = InvoiceLineItem.objects.filter(invoice__client=self)
        old_invoice_set = invoice_set.filter(
            invoice__date__lt=date(2012, 9, 1)
        )
        return agg_total(payment_set) + agg_total(old_invoice_set)

    def owed(self):
        return self.billed() - self.paid()
    owed.short_description = 'Balance'

    def get_absolute_url(self):
        return reverse('statement', args=[self.name])

    def clean(self):
        if self.owed() and not self.active:
            raise ValidationError("Cannot inactivate client with balance.")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Document(models.Model):
    client = models.ForeignKey(Client)
    no = DocumentNoField(unique=True)
    date = models.DateField(default=date.today)
    name = models.CharField(max_length=127, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        if self.name:
            return "%s (%s)" % (self.no, self.name[:25])
        else:
            return str(self.no)

    class Meta:
        abstract = True
        ordering = ['-no']


class Project(Document):
    def amount(self):
        invoice_set = InvoiceLineItem.objects.filter(invoice__project=self)
        return agg_total(invoice_set)


class Invoice(Document):
    project = models.ForeignKey(Project)

    @property
    def amount(self):
        return agg_total(self.invoicelineitem_set)

    @property
    def paid(self):
        if self.date < date(2012, 9, 1):
            return agg_total(self.invoicelineitem_set)
        return agg_total(self.payment_set)

    @property
    def balance(self):
        return self.amount - self.paid

    def is_paid(self):
        if self.balance <= 0:
            return True
        else:
            return False
    is_paid.boolean = True
    is_paid.short_description = 'Paid?'

    def get_absolute_url(self):
        return reverse('invoice', args=[self.no])

    def clean(self):
        if (hasattr(self, 'client') and hasattr(self, 'project') and
                self.client != self.project.client):
            raise ValidationError(
                "Project and invoice must have the same client.")


class InvoiceLineAction(models.Model):
    name = models.CharField(unique=True, max_length=31)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class InvoiceLineItem(models.Model):
    position = models.PositiveSmallIntegerField()
    invoice = models.ForeignKey(Invoice)
    date = models.DateField(default=date.today)
    description = models.TextField()
    qty = models.DecimalField(max_digits=6, decimal_places=3)
    action = models.ForeignKey(InvoiceLineAction, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)

    @property
    def amount(self):
        if self.unit_price and self.qty:
            return (self.unit_price * self.qty).quantize(Decimal('.01'))
        else:
            return 0

    @property
    def client(self):
        return self.project.client

    def is_billed(self):
        if self.invoice:
            return True
        else:
            return False
    is_billed.boolean = True
    is_billed.admin_order_field = 'invoice'
    is_billed.short_description = 'Billed?'

    def __str__(self):
        return "%s: %s" % (self.invoice, self.description[:40])

    class Meta:
        ordering = ['invoice', 'position', 'date']


class Payment(models.Model):
    invoice = models.ForeignKey(Invoice)
    date = models.DateField(default=date.today)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    notes = models.TextField(blank=True)

    @property
    def client(self):
        return self.invoice.client

    def __str__(self):
        return "%s: %s" % (self.invoice, self.amount)
