from dal.autocomplete import ModelSelect2
from django import forms

from armgmt.models import (Document, Client, Project, Invoice, Task,
                           get_document_no)


class DocumentForm(forms.ModelForm):
    """Form for Projects and Invoices.

    Modifications of this model form:

     - Auto-increment document no field to maximum no + 1.
     - Limits client drop-down options to active clients.
     - Limits project drop-down options to the client's projects.

    """

    def __init__(self, *args, **kwargs):
        super(DocumentForm, self).__init__(*args, **kwargs)

        # Auto-increment document no field.
        if 'no' in self.fields:
            self.fields['no'].initial = get_document_no(self.Meta.model)

        # Limit client drop-down options to active clients.
        if 'client' in self.fields:
            self.fields['client'].queryset = \
                Client.objects.filter(active=True)

    class Meta:
        model = Document
        exclude = []
        widgets = {
            'project': ModelSelect2(url='autocomplete-project',
                                    forward=['client']),
        }


class InvoiceLineItemForm(forms.ModelForm):
    """Form for invoice line items.

    This form makes the content text box smaller.

    """
    content = forms.CharField(widget=forms.Textarea)


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
            'client': ModelSelect2(url='autocomplete-client',
                                   forward=['invoice', 'project']),
            'invoice': ModelSelect2(url='autocomplete-invoice',
                                    forward=['client', 'project']),
            'project': ModelSelect2(url='autocomplete-project',
                                    forward=['client', 'invoice']),
        }


class ToolForm(forms.Form):
    """Form for generating reports from file upload."""

    files = forms.FileField(widget=forms.ClearableFileInput(
        attrs={'multiple': True}
    ))
