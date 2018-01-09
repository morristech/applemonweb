from datetime import date
from decimal import Decimal
from numbers import Number
import re

from django import forms
from django.conf import settings
from django.db import models
from django.db.models import Max
from django.core.exceptions import ValidationError
from django.urls import reverse
from localflavor.us.models import USStateField, USZipCodeField
from phonenumber_field.modelfields import PhoneNumberField
from usps.addressinformation import Address, USPSXMLError


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


def clean_address(s):
    """Sanitize mailing address fields by removing punctuation."""
    s = ''.join(i for i in s if i.isalnum() or i.isspace() or i in '/\'-&')
    return ' '.join(s.split())


def get_default_biller_id():
    """Return default biller if exists or the first primary id."""
    try:
        return Biller.objects.get(code='C').pk
    except Biller.DoesNotExist:
        return 1


def get_document_no(document, biller=None):
    """Generate a document no by incrementing maximum no."""
    if not biller:
        biller = get_default_biller_id()
    qs = document.objects.filter(biller=biller)
    max_document_no = qs.aggregate(Max('no'))['no__max']
    if max_document_no and max_document_no != 'None':
        return DocumentNo(max_document_no) + 1


def str2num(s, fmt=tuple):
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
    if fmt == tuple:
        # Format year and number as a tuple.
        return (yy, num)
    else:
        # Format based on a number of form yynum.
        return fmt(yy * 1000 + num)


def validate_seq_documents(cls, biller, new_no=None):
    """Validate that document no are all sequential."""
    q = cls.objects.filter(biller=biller).values_list('no').order_by()
    if new_no:
        new_no = DocumentNo(new_no)
        q = q.filter(no__lt=new_no)
    nos = [DocumentNo(i[0]) for i in q]
    if new_no:
        nos.append(new_no)
    old_no = None
    for no in nos:
        if no[0] < 11:
            # Ignore missing data before 2011.
            continue
        if old_no and old_no[0] == no[0] and old_no + 1 != no:
            raise ValidationError(
                "{doc} not sequential - missing {doc} {no}.".format(
                    doc=cls.__name__, no=old_no + 1
                )
            )
        old_no = no


class DocumentNo(tuple):
    __slots__ = []

    def __new__(cls, value):
        if value is None:
            return None
        elif isinstance(value, DocumentNo):
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

    def formfield(self, form_class=None, choices_form_class=None, **kwargs):
        if not form_class:
            form_class = forms.CharField
        if 'validators' not in kwargs:
            kwargs['validators'] = []
        if validate_DocumentNo not in kwargs['validators']:
            kwargs['validators'].append(validate_DocumentNo)
        kwargs['max_length'] = 6
        kwargs['required'] = False
        return super(DocumentNoField, self).formfield(
            form_class, choices_form_class, **kwargs
        )


class Entity(models.Model):
    name = models.CharField(unique=True, max_length=127)
    firm_name = models.CharField(max_length=127, blank=True)
    address1 = models.CharField(max_length=127, blank=True)
    address2 = models.CharField(max_length=127)
    city = models.CharField(max_length=127)
    state = USStateField()
    zip_code = USZipCodeField()
    phone_number = PhoneNumberField(blank=True)
    fax_number = PhoneNumberField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        abstract = True
        ordering = ['name']


class Biller(Entity):
    firm_name = models.CharField(max_length=127)
    code = models.CharField(unique=True, max_length=1)

    class Meta:
        ordering = ['code']


class Client(Entity):
    biller = models.ForeignKey(Biller, default=get_default_biller_id,
                               on_delete=models.CASCADE)
    contact_name = models.CharField(max_length=127)
    notes = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    address_validation = models.TextField(blank=True)

    @property
    def address(self):
        if self.firm_name:
            n2 = '\n{}'.format(self.firm_name)
        else:
            n2 = ''
        return "ATTN {n1}{n2}\n{a2} {a1}\n{city} {state}  {zip_code}".format(
            n1=self.contact_name, n2=n2,
            a1=self.address1, a2=self.address2,
            city=self.city, state=self.state, zip_code=self.zip_code
        ).upper()

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
        super(Client, self).clean()
        if self.owed() and not self.active:
            raise ValidationError("Cannot inactivate client with balance.")
        self.contact_name = clean_address(self.contact_name)
        self.firm_name = clean_address(self.firm_name)
        if '-' in self.zip_code:
            (zip5, zip4) = self.zip_code.split('-')
        else:
            zip5 = self.zip_code
            zip4 = ''
        address_validator = Address(user_id=settings.SECRETS['USPS_USER_ID'])
        try:
            address_response = address_validator.validate(
                address1=self.address1, address2=self.address2,
                city=self.city, state=self.state, zip_5=zip5, zip_4=zip4)
        except USPSXMLError as e:
            raise ValidationError(e)
        if 'Address1' in address_response:
            self.address1 = address_response['Address1']
        self.address2 = address_response['Address2']
        self.city = address_response['City']
        self.state = address_response['State']
        if address_response['Zip4']:
            self.zip_code = address_response['FullZip']
        else:
            self.zip_code = address_response['Zip5']
        if 'ReturnText' in address_response and address_response['ReturnText']:
            self.address_validation = address_response['ReturnText']
        else:
            self.address_validation = "Validated by USPS."


class Document(models.Model):
    biller = models.ForeignKey(Biller, default=get_default_biller_id,
                               on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    no = DocumentNoField()
    name = models.CharField(max_length=127, blank=True)
    content = models.TextField(blank=True)

    def clean(self):
        if self.content and not self.name:
            self.name = re.match(
                '([ -]{0,1}\w+){0,12}',
                " ".join(self.content.split()).strip()
            ).group()
        if (self.client_id and self.client.biller and
                not hasattr(self, 'biller')):
            # Fill in biller from client.
            self.biller = self.client.biller
        if self.biller_id and self.biller != self.client.biller:
            raise ValidationError(
                "Client must have the same biller.")

    def __str__(self):
        if self.name:
            return "%s (%s)" % (self.code, self.name[:25])
        else:
            return str(self.code)

    class Meta:
        abstract = True
        ordering = ['-no']
        unique_together = ('biller', 'no')


class Project(Document):
    start_date = models.DateField(default=date.today)
    end_date = models.DateField(null=True, blank=True)

    @property
    def code(self):
        return "{biller}P{no}".format(biller=self.biller.code, no=self.no)

    def amount(self):
        invoice_set = InvoiceLineItem.objects.filter(invoice__project=self)
        return agg_total(invoice_set)

    def clean(self):
        super(Project, self).clean()
        if not self.no:
            self.no = get_document_no(Project, self.biller)
        if self.end_date and self.start_date > self.end_date:
            raise ValidationError("Project start date must precede end date.")


class Invoice(Document):
    date = models.DateField(default=date.today)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)

    @property
    def code(self):
        return "{biller}N{no}".format(biller=self.biller.code, no=self.no)

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
        return bool(self.balance <= 0)
    is_paid.boolean = True
    is_paid.short_description = 'Paid?'

    def get_absolute_url(self):
        return reverse('invoice', args=[self.biller.code, self.no])

    def clean(self):
        super(Invoice, self).clean()
        if (self.project_id and self.project.biller and
                not hasattr(self, 'biller')):
            # Fill in biller from project.
            self.biller = self.project.biller
        if (self.project_id and self.project.client and
                not hasattr(self, 'client')):
            # Fill in client from project.
            self.client = self.project.client
        if self.biller_id and self.biller != self.project.biller:
            raise ValidationError(
                "Project must have the same biller.")
        if self.client_id and self.client != self.project.client:
            raise ValidationError(
                "Project must have the same client.")
        if not self.no:
            self.no = get_document_no(Invoice, self.biller)
        validate_seq_documents(Invoice, self.biller, self.no)


class InvoiceLineAction(models.Model):
    name = models.CharField(unique=True, max_length=31)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class InvoiceLineItem(models.Model):
    position = models.PositiveSmallIntegerField()
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    date = models.DateField(default=date.today)
    content = models.TextField()
    qty = models.DecimalField(max_digits=6, decimal_places=3)
    action = models.ForeignKey(
        InvoiceLineAction, on_delete=models.SET_NULL,
        null=True, blank=True,
    )
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
        return bool(self.invoice)
    is_billed.boolean = True
    is_billed.admin_order_field = 'invoice'
    is_billed.short_description = 'Billed?'

    def __str__(self):
        return "%s: %s" % (self.invoice, self.content[:40])

    class Meta:
        ordering = ['invoice', 'position', 'date']


class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    date = models.DateField(default=date.today)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    notes = models.TextField(blank=True)

    @property
    def client(self):
        return self.invoice.client

    def __str__(self):
        return "%s: %s" % (self.invoice, self.amount)

    class Meta:
        ordering = ['-date', '-invoice__no']


class Task(models.Model):
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='tasks_assigned',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='tasks_authored',
    )
    date_opened = models.DateField(default=date.today)
    date_due = models.DateField(null=True, blank=True)
    date_closed = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=8, default='new', choices=[
        ('new', "New"),
        ('open', "Open"),
        ('done', "Done"),
        ('archived', "Archived"),
    ])
    name = models.CharField(max_length=127)
    content = models.TextField(blank=True)
    biller = models.ForeignKey(
        Biller, on_delete=models.SET_NULL, null=True, blank=True,
    )
    client = models.ForeignKey(
        Client, on_delete=models.SET_NULL, null=True, blank=True,
    )
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True,
    )
    invoice = models.ForeignKey(
        Invoice, on_delete=models.SET_NULL, null=True, blank=True,
    )

    def clean(self):
        if self.project and not self.biller:
            # Fill in biller from project.
            self.biller = self.project.biller
        if self.project and not self.client:
            # Fill in client from project.
            self.client = self.project.client
        if self.invoice:
            if not self.biller:
                # Fill in biller from invoice.
                self.biller = self.invoice.biller
            if not self.client:
                # Fill in client from invoice.
                self.client = self.invoice.client
            if not self.project:
                # Fill in project from invoice.
                self.project = self.invoice.project
        if self.date_closed and self.status not in ['done', 'archived']:
            raise ValidationError(
                "Closed task must be marked done or archived."
            )
        if self.date_due and self.date_due < self.date_opened:
            raise ValidationError("Task must be due after date opened.")
        if self.date_closed and self.date_closed < self.date_opened:
            raise ValidationError("Task must be closed after date opened.")
        if self.status in ['done', 'archived']:
            raise ValidationError("Done task must record date closed (today?)")
        if (self.biller and self.project and
                self.biller != self.project.biller):
            raise ValidationError("Project must have the same biller.")
        if (self.biller and self.invoice and
                self.biller != self.invoice.biller):
            raise ValidationError("Invoice must have the same biller.")
        if (self.client and self.project and
                self.client != self.project.client):
            raise ValidationError("Project must have the same client.")
        if (self.client and self.invoice and
                self.client != self.invoice.client):
            raise ValidationError("Invoice must have the same client.")
        if (self.project and self.invoice and
                self.project != self.invoice.project):
            raise ValidationError("Invoice must have the same project.")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['date_due', 'date_opened']
