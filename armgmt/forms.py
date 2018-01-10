from dal.autocomplete import ListSelect2, ModelSelect2
from django import forms
from django.contrib.admin.widgets import AdminDateWidget

from armgmt.models import (Biller, Client, Document, Project, Invoice,
                           Payment, Task, get_document_no)


def select(url, forward=None):
    """Build Select2 autocomplete widget with default fields."""
    forwards = ['biller', 'client', 'project', 'invoice']
    if forward:
        forwards += forward
    if url.endswith('no'):
        cls = ListSelect2
    else:
        cls = ModelSelect2
    return cls(
        url=url,
        forward=forwards,
    )


class DateWidget(AdminDateWidget):
    """Override AdminDateWidget to avoid explicitly loading jQuery.

    AdminDateWidget breaks django-autocomplete-light when DateField
    is assigned later in the model because jQuery is then
    loaded after dal. So override media to avoid ordering jQuery.

    See:
    https://github.com/yourlabs/django-autocomplete-light/issues/959

    """

    @property
    def media(self):
        js = [
            'jquery.init.js',
            'calendar.js',
            'admin/DateTimeShortcuts.js',
        ]
        return forms.Media(js=['admin/js/%s' % path for path in js])


class DocumentForm(forms.ModelForm):
    """Base form for Projects and Invoices.

    Modifications of this model form:

     - Auto-increment document no field to maximum no + 1.
     - Includes initial/saved document no in autocomplete widget choices.
     - Limits client drop-down options to active clients.

    """

    def __init__(self, *args, **kwargs):
        super(DocumentForm, self).__init__(*args, **kwargs)

        # Auto-increment document no field.
        # Add initial/saved document no to autocomplete widget choices.
        if 'no' in self.fields:
            self.fields['no'].initial = str(get_document_no(self.Meta.model))
            if self.instance.no:
                self.fields['no'].widget.choices = [
                    [self.instance.no, self.instance.no]
                ]
            else:
                self.fields['no'].widget.choices = [
                    [self.fields['no'].initial, self.fields['no'].initial]
                ]

        # Limit client drop-down options to active clients.
        if 'client' in self.fields:
            self.fields['client'].queryset = \
                Client.objects.filter(active=True)

    class Meta:
        model = Document
        exclude = []


class ProjectForm(DocumentForm):
    """Form with autocomplete widgets for Projects."""

    class Meta:
        model = Project
        exclude = []
        widgets = {
            'start_date': DateWidget,
            'end_date': DateWidget,
            'client': select('autocomplete-client'),
            'no': select('autocomplete-projectno'),
        }


class InvoiceForm(DocumentForm):
    """Form with autocomplete widgets for Invoices."""

    class Meta:
        model = Invoice
        exclude = []
        widgets = {
            'date': DateWidget,
            'client': select('autocomplete-client'),
            'no': select('autocomplete-invoiceno'),
            'project': select('autocomplete-project'),
        }


class InvoiceLineItemForm(forms.ModelForm):
    """Form for invoice line items.

    This form makes the content text box smaller.

    """
    content = forms.CharField(widget=forms.Textarea)


class PaymentForm(forms.ModelForm):
    """Form with optional autocomplete fields for Payments."""

    biller = forms.ModelChoiceField(
        queryset=Biller.objects.all(),
        required=False,
    )
    client = forms.ModelChoiceField(
        queryset=Client.objects.all(),
        widget=select('autocomplete-client'),
        required=False,
    )
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        widget=select('autocomplete-project'),
        required=False,
    )

    class Meta:
        model = Payment
        exclude = []
        widgets = {
            'date': DateWidget,
            'invoice': select('autocomplete-invoice'),
        }


class TaskForm(forms.ModelForm):
    """Form for Tasks.

    Modifications of this model form:

     - Limits client drop-down options to active clients.
     - Limits project/invoice drop-down options to the client's.
     - Limits invoice drop-down options to the project's invoices.

    """

    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)

        # Fill in author with current user.
        if hasattr(self, 'current_user') and self.current_user:
            self.fields['author'].initial = self.current_user

    class Meta:
        model = Task
        exclude = []
        widgets = {
            'client': select('autocomplete-client'),
            'project': select('autocomplete-project'),
            'invoice': select('autocomplete-invoice'),
        }


class ToolForm(forms.Form):
    """Form for generating reports from file upload."""

    files = forms.FileField(widget=forms.ClearableFileInput(
        attrs={'multiple': True}
    ))
