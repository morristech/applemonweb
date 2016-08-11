from django.contrib import admin
from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

from armgmt.models import (Client, Project,
                           Invoice, InvoiceLineItem, InvoiceLineAction,
                           Payment, Task)
from armgmt.forms import DocumentForm, InvoiceLineItemForm, TaskForm


# Customize admin site appearance.
admin.AdminSite.site_header = "Applemon"
admin.AdminSite.site_title = "Admin"
admin.AdminSite.index_title = "Applemon DB"

# Do not manage groups in admin site.
admin.site.unregister(Group)


class ProjectInline(admin.TabularInline):
    model = Project
    fields = ['No', 'start_date', 'end_date', 'name', 'amount']
    readonly_fields = ['No', 'amount']
    extra = 0
    max_num = 0

    def No(self, instance):
        """Link Project No to ProjectAdmin."""
        url = reverse('admin:armgmt_project_change', args=(instance.id,))
        return mark_safe("<a href='%s'>%s</a>" % (url, instance.no))


class InvoiceInline(admin.TabularInline):
    model = Invoice
    fields = ['No', 'date', 'name', 'amount', 'is_paid']
    readonly_fields = ['No', 'amount', 'is_paid']
    extra = 0
    max_num = 0

    def No(self, instance):
        """Link Invoice No to InvoiceAdmin."""
        url = reverse('admin:armgmt_invoice_change', args=(instance.id,))
        return mark_safe("<a href='%s'>%s</a>" % (url, instance.no))


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    form = InvoiceLineItemForm
    readonly_fields = ['amount']
    sortable_field_name = 'position'
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


class TaskInline(admin.TabularInline):
    model = Task
    form = TaskForm
    extra = 0
    fields = ['name', 'assignee', 'author', 'date_opened', 'status',
              'client', 'project', 'invoice', 'Edit']
    readonly_fields = ['Edit']

    def Edit(self, instance):
        """Link Task Name to TaskAdmin."""
        url = reverse('admin:armgmt_task_change', args=(instance.id,))
        return mark_safe('<a href="%s">Edit</a>' % url)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    inlines = [TaskInline, ProjectInline, InvoiceInline]
    list_display = ['name', 'owed']
    list_filter = ['active']
    readonly_fields = ['billed', 'paid', 'owed']
    search_fields = ['name', 'notes']

    def changelist_view(self, request, extra_context=None):
        """Filter only active clients by default."""
        if 'active__exact' not in request.GET:
            q = request.GET.copy()
            q['active__exact'] = 1
            request.GET = q
            request.META['QUERY_STRING'] = request.GET.urlencode()
        return super(ClientAdmin, self).changelist_view(
            request,
            extra_context=extra_context)


class DocumentAdmin(admin.ModelAdmin):
    list_display_links = ['no']
    list_filter = ['client']
    list_per_page = 100
    search_fields = ['no', 'name', 'content', 'client__name']
    form = DocumentForm

    def get_search_results(self, request, queryset, search_term):
        # TODO: hack to treat DocumentNo as an integer by removing hyphen.
        search_term = search_term.replace('-', '')
        return super(
            DocumentAdmin, self
        ).get_search_results(request, queryset, search_term)


@admin.register(Project)
class ProjectAdmin(DocumentAdmin):
    inlines = [TaskInline, InvoiceInline]
    list_display = ['client', 'no', 'start_date', 'end_date',
                    'name', 'amount']
    readonly_fields = ['amount']
    date_hierarchy = 'start_date'


@admin.register(Invoice)
class InvoiceAdmin(DocumentAdmin):
    inlines = [TaskInline, InvoiceLineItemInline, PaymentInline]
    list_display = ['is_paid', 'client', 'no', 'date', 'name', 'amount',
                    'paid']
    readonly_fields = ['is_paid', 'amount', 'paid', 'balance']
    date_hierarchy = 'date'


@admin.register(InvoiceLineAction)
class InvoiceLineActionAdmin(admin.ModelAdmin):
    pass


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['client', 'invoice', 'date', 'amount']
    list_display_links = ['amount']
    list_filter = ['invoice__client']
    ordering = ['-invoice', '-date']
    date_hierarchy = 'date'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    form = TaskForm
    list_display = ['assignee', 'name', 'status',
                    'client', 'project', 'invoice', 'date_due', 'date_opened']
    list_display_links = ['name']
    list_filter = ['status', 'assignee', 'author']
    search_fields = ['name', 'content', 'status',
                     'assignee__username', 'author__username']
    ordering = ['date_due', 'date_opened']
    date_hierarchy = 'date_opened'

    def get_form(self, request, *args, **kwargs):
        """Override get_form to pass request.user to form."""
        form = super(TaskAdmin, self).get_form(request, *args, **kwargs)
        form.current_user = request.user
        return form
