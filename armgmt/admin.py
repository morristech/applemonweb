from django.contrib import admin
from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

from armgmt.models import Client, Project, Invoice, Action, Service, Payment
from armgmt.forms import DocumentForm, ServiceForm


# Customize admin site appearance.
admin.AdminSite.site_header = "Applemon"
admin.AdminSite.site_title = "Admin"
admin.AdminSite.index_title = "Applemon DB"

# Do not manage groups in admin site.
admin.site.unregister(Group)


class ProjectInline(admin.TabularInline):
    model = Project
    fields = ['No', 'date', 'name', 'amount']
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


class ServiceInline(admin.TabularInline):
    model = Service
    form = ServiceForm
    readonly_fields = ['amount']
    sortable_field_name = 'position'
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    inlines = [ProjectInline, InvoiceInline]
    list_display = ['name', 'owed']
    list_filter = ['active']
    readonly_fields = ['billed', 'paid', 'owed']
    search_fields = ['name', 'notes']

    def changelist_view(self, request, extra_context=None):
        """Filter only active clients by default."""
        if not 'active__exact' in request.GET:
            q = request.GET.copy()
            q['active__exact'] = 1
            request.GET = q
            request.META['QUERY_STRING'] = request.GET.urlencode()
        return super(ClientAdmin, self).changelist_view(request,
            extra_context=extra_context)


class DocumentAdmin(admin.ModelAdmin):
    list_display_links = ['no']
    #list_editable = ['name']
    list_filter = ['client']
    list_per_page = 100
    date_hierarchy = 'date'
    search_fields = ['no', 'name', 'description', 'client__name']
    form = DocumentForm

    def get_search_results(self, request, queryset, search_term):
        # TODO: hack to treat DocumentNo as an integer by removing hyphen.
        search_term = search_term.replace('-', '')
        return super(DocumentAdmin, self
            ).get_search_results(request, queryset, search_term)


@admin.register(Project)
class ProjectAdmin(DocumentAdmin):
    inlines = [InvoiceInline]
    list_display = ['client', 'no', 'date', 'name', 'amount']
    readonly_fields = ['amount']


@admin.register(Invoice)
class InvoiceAdmin(DocumentAdmin):
    inlines = [ServiceInline, PaymentInline]
    list_display = ['is_paid', 'client', 'no', 'date', 'name', 'amount',
                    'paid']
    readonly_fields = ['is_paid', 'amount', 'paid', 'balance']


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    #def get_model_perms(self, request):
    #    return {}
    #inlines = [ServiceInline]
    pass

#@admin.register(Service)
#class ServiceAdmin(admin.ModelAdmin):
#    list_display = ['is_billed', 'invoice__client', 'invoice__project',
#                    'invoice', 'date', 'description', 'amount']
#    list_display_links = ['date', 'description']
#    list_filter = ['invoice__client']
#    list_per_page = 50
#    ordering = ['-invoice', '-date', 'description']
#    date_hierarchy = 'date'
#    search_fields = ['description', 'action__name',
#                     'invoice__project__name', 'invoice__project__description',
#                     'invoice__name', 'invoice__description']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['client', 'invoice', 'date', 'amount']
    list_display_links = ['amount']
    list_filter = ['invoice__client']
    ordering = ['-invoice', '-date']
    date_hierarchy = 'date'
