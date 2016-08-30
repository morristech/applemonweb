from django import forms
from django.db.models import Max

from armgmt.models import DocumentNo, Document, Client, Project, Invoice, Task


class DocumentForm(forms.ModelForm):
    """Form for Projects and Invoices.

    Modifications of this model form:

     - Auto-increment document no field to maximum no + 1.
     - Limits client drop-down options to active clients.
     - Limits project drop-down options to the client's projects.

    """

    def __init__(self, *args, **kwargs):
        super(DocumentForm, self).__init__(*args, **kwargs)

        # Auto-increment document no field to maximum no + 1.
        if 'no' in self.fields:
            document = self.Meta.model
            max_document_no = document.objects.aggregate(Max('no'))['no__max']
            if max_document_no and max_document_no != 'None':
                self.fields['no'].initial = DocumentNo(max_document_no) + 1

        # Limit client drop-down options to active clients.
        if 'client' in self.fields:
            self.fields['client'].queryset = \
                Client.objects.filter(active=True)

        # Limit project drop-down options to client's projects.
        if 'project' in self.fields and hasattr(self.instance, 'client'):
            client = self.instance.client
            if client:
                self.fields['project'].queryset = \
                    Project.objects.filter(client=client)

    class Meta:
        model = Document
        exclude = []


class InvoiceLineItemForm(forms.ModelForm):
    """Form for invoice line items.

    The form hides position and makes the content text box smaller.

    """
    position = forms.CharField(widget=forms.HiddenInput)
    content = forms.CharField(widget=forms.Textarea)


class InvoiceForm1(DocumentForm):
    """Invoice form page 1: enter client, no, date."""

    class Meta:
        model = Invoice
        fields = ['client', 'no', 'date']


class InvoiceForm2(DocumentForm):
    """Invoice form page 2: choose from client's projects."""

    def __init__(self, client, *args, **kwargs):
        """Accept additional client argument from wizard to limit projects."""
        super(InvoiceForm2, self).__init__(*args, **kwargs)

        # Limit project drop-down options to client's projects.
        if client:
            self.fields['project'].queryset = \
                Project.objects.filter(client=client)

    class Meta:
        model = Invoice
        fields = ['project']


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

        # Limit client drop-down options to active clients.
        if 'client' in self.fields:
            self.fields['client'].queryset = \
                Client.objects.filter(active=True)

        # Limit project and invoice drop-down options to client's
        # projects and invoices.
        if hasattr(self.instance, 'client') and self.instance.client:
            client = self.instance.client
            if 'project' in self.fields:
                self.fields['project'].queryset = \
                    Project.objects.filter(client=client)
            if 'invoice' in self.fields:
                self.fields['invoice'].queryset = \
                    Invoice.objects.filter(client=client)

        # Limit invoice drop-down options to project's invoices.
        if 'invoice' in self.fields and hasattr(self.instance, 'project'):
            project = self.instance.project
            if project:
                self.fields['invoice'].queryset = \
                    Invoice.objects.filter(project=project)

    class Meta:
        model = Task
        exclude = []
