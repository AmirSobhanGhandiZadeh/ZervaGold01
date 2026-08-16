from django.contrib import admin

from apps.tenancy.models import Membership, Organization, OrganizationContract


class OrganizationContractInline(admin.StackedInline):
    model = OrganizationContract
    extra = 0


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    fk_name = "organization"


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["display_name", "organization_type", "status", "created_at"]
    list_filter = ["organization_type", "status"]
    search_fields = ["display_name", "legal_name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [OrganizationContractInline, MembershipInline]


@admin.register(OrganizationContract)
class OrganizationContractAdmin(admin.ModelAdmin):
    list_display = ["organization", "contract_reference", "status", "signed_at"]
    list_filter = ["status"]
    search_fields = ["organization__display_name", "contract_reference"]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "organization", "membership_role", "status", "created_at"]
    list_filter = ["membership_role", "status"]
    search_fields = ["user__mobile_e164", "organization__display_name"]
