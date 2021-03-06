from django.contrib import admin
from django.contrib.auth.models import Group
from django.db.models.fields import CharField

from armgmt.models import (Biller, Client, Project,
                           Invoice, InvoiceLineItem, InvoiceLineAction,
                           Payment, Task)
from armgmt.forms import (DocumentForm, ProjectForm, InvoiceForm,
                          InvoiceLineItemForm, PaymentForm, TaskForm)


# Customize admin site appearance.
admin.AdminSite.site_header = "Applemon"
admin.AdminSite.site_title = "Admin"
admin.AdminSite.index_title = "Applemon DB"

# Do not manage groups in admin site.
admin.site.unregister(Group)


class ProjectInline(admin.TabularInline):
    model = Project
    form = ProjectForm
    fields = ['no', 'start_date', 'end_date', 'name', 'amount']
    readonly_fields = fields
    can_delete = False
    show_change_link = True
    extra = 0
    max_num = 0


class InvoiceInline(admin.TabularInline):
    model = Invoice
    form = InvoiceForm
    fields = ['no', 'date', 'name', 'amount', 'is_paid']
    readonly_fields = fields
    can_delete = False
    show_change_link = True
    extra = 0
    max_num = 0


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
              'client', 'project', 'invoice']
    can_delete = False
    show_change_link = True


@admin.register(Biller)
class BillerAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'firm_name', 'city', 'state',
                    'phone_number']
    list_display_links = ['name']


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    inlines = [TaskInline, ProjectInline, InvoiceInline]
    list_display = ['name', 'firm_name', 'contact_name', 'city', 'state',
                    'phone_number', 'owed']
    list_filter = ['biller', 'active']
    readonly_fields = ['address', 'address_validation',
                       'billed', 'paid', 'owed']
    search_fields = [f.name for f in Client._meta.get_fields()
                     if isinstance(f, CharField)] + ['notes']
    save_on_top = True

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
    form = DocumentForm
    list_display_links = ['code']
    list_filter = ['biller', 'client']
    list_per_page = 100
    search_fields = ['no', 'name', 'content', 'client__name', 'client__notes']
    save_as = True
    save_on_top = True

    def get_search_results(self, request, queryset, search_term):
        # TODO: hack to treat DocumentNo as an integer by removing hyphen.
        search_term = search_term.replace('-', '')
        return super(
            DocumentAdmin, self
        ).get_search_results(request, queryset, search_term)


@admin.register(Project)
class ProjectAdmin(DocumentAdmin):
    form = ProjectForm
    inlines = [TaskInline, InvoiceInline]
    list_display = ['client', 'code', 'start_date', 'end_date',
                    'name', 'amount']
    readonly_fields = ['code', 'amount']
    date_hierarchy = 'start_date'
    search_fields = DocumentAdmin.search_fields + \
        ['task__name', 'task__content', 'invoice__name', 'invoice__content']


@admin.register(Invoice)
class InvoiceAdmin(DocumentAdmin):
    form = InvoiceForm
    inlines = [TaskInline, InvoiceLineItemInline, PaymentInline]
    list_display = ['is_paid', 'client', 'code', 'date', 'name',
                    'amount', 'paid']
    readonly_fields = ['code', 'is_paid', 'amount', 'paid', 'balance']
    date_hierarchy = 'date'
    search_fields = DocumentAdmin.search_fields + \
        ['project__name', 'project__content', 'task__name', 'task__content',
         'invoicelineitem__content', 'payment__notes']


@admin.register(InvoiceLineAction)
class InvoiceLineActionAdmin(admin.ModelAdmin):
    pass


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    form = PaymentForm
    list_display = ['client', 'invoice', 'date', 'amount']
    list_display_links = ['amount']
    list_filter = ['invoice__biller', 'invoice__client']
    date_hierarchy = 'date'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    form = TaskForm
    list_display = ['assignee', 'name', 'status',
                    'client', 'project', 'invoice', 'date_due', 'date_opened']
    list_display_links = ['name']
    list_filter = ['status', 'assignee', 'author']
    search_fields = ['name', 'content', 'status',
                     'assignee__username', 'author__username',
                     'client__name', 'client__notes',
                     'project__name', 'project__content',
                     'invoice__name', 'invoice__content']
    date_hierarchy = 'date_opened'
    save_on_top = True

    def get_form(self, request, obj=None, **kwargs):
        """Override get_form to pass request.user to form."""
        form = super(TaskAdmin, self).get_form(request, obj, **kwargs)
        form.current_user = request.user
        return form
