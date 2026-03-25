from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from naming.models import (
    DataCenter,
    HypervisorOS,
    NamingRequest,
    NetworkConfiguration,
    ServerAllocation,
    VirtualMachine,
)


@admin.register(DataCenter)
class DataCenterAdmin(admin.ModelAdmin):
    list_display = ("start_name", "end_name", "count_of_servers", "start_numbers", "end_numbers", "is_active")
    list_filter = ("is_active",)
    search_fields = ("start_name", "end_name")


@admin.register(NamingRequest)
class NamingRequestAdmin(admin.ModelAdmin):
    list_display = ("pk", "created_by", "data_center", "status", "created_at", "submitted_at", "approved_at")
    list_filter = ("status", "data_center")
    search_fields = ("pk",)


@admin.register(ServerAllocation)
class ServerAllocationAdmin(admin.ModelAdmin):
    list_display = ("server_name", "server_number", "data_center", "naming_request", "management_ip")
    search_fields = ("server_name",)


@admin.register(HypervisorOS)
class HypervisorOSAdmin(admin.ModelAdmin):
    list_display = ("hv_os_name", "server", "hypervisor_type_os_type", "management_ip", "ports", "version_build_number")
    search_fields = ("hv_os_name", "hypervisor_type_os_type")


@admin.register(VirtualMachine)
class VirtualMachineAdmin(admin.ModelAdmin):
    list_display = ("vm_name", "hypervisor", "management_ip", "os", "application_name")
    search_fields = ("vm_name", "application_name")


@admin.register(NetworkConfiguration)
class NetworkConfigurationAdmin(admin.ModelAdmin):
    list_display = ("server", "server_port_name", "connection_type", "network_role", "uplink_hostname", "uplink_interface")
    search_fields = ("server_port_name", "uplink_interface", "uplink_hostname")
