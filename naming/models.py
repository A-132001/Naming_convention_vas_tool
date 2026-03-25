from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class DataCenter(models.Model):
    """
    Admin-defined naming blocks.

    Server name format:
        {start_name}-SR{server_number}C-{end_name}
    """

    start_name = models.CharField(max_length=64, unique=True)
    end_name = models.CharField(max_length=64)
    count_of_servers = models.PositiveIntegerField()
    start_numbers = models.PositiveIntegerField()
    end_numbers = models.PositiveIntegerField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_name"]

    def __str__(self) -> str:
        return self.start_name

    def clean(self) -> None:
        if self.start_numbers > self.end_numbers:
            raise models.ValidationError("start_numbers must be <= end_numbers")
        max_possible = (self.end_numbers - self.start_numbers) + 1
        if self.count_of_servers > max_possible:
            raise models.ValidationError(
                "count_of_servers cannot exceed the available numbers in the range"
            )


class NamingRequest(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="naming_requests",
    )
    data_center = models.ForeignKey(
        DataCenter,
        on_delete=models.PROTECT,
        related_name="naming_requests",
    )

    # The user submits steps 1..4 in order; final submit transitions to PENDING.
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    step1_completed = models.BooleanField(default=False)
    step2_completed = models.BooleanField(default=False)
    step3_completed = models.BooleanField(default=False)
    step4_completed = models.BooleanField(default=False)

    requested_server_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )

    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    finalized_by_admin_at = models.DateTimeField(null=True, blank=True)

    rejected_snapshot_json = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Request #{self.pk} ({self.get_status_display()})"

    @property
    def is_editable_by_user(self) -> bool:
        return self.status == self.Status.DRAFT

    @property
    def is_pending_review(self) -> bool:
        return self.status == self.Status.PENDING


class ServerAllocation(models.Model):
    """
    A reserved server number within a DataCenter block for a specific request.
    """

    naming_request = models.ForeignKey(
        NamingRequest,
        on_delete=models.CASCADE,
        related_name="server_allocations",
    )
    data_center = models.ForeignKey(
        DataCenter,
        on_delete=models.PROTECT,
        related_name="server_allocations",
    )

    server_number = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    server_name = models.CharField(max_length=255, unique=True)

    # Step 1: user provides management IP. During "generate servers" we reserve the
    # server numbers, then we fill management_ip during Step 1 submission.
    management_ip = models.GenericIPAddressField(
        protocol="IPv4",
        null=True,
        blank=True,
        help_text="Provided in Step 1 submission.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["server_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["data_center", "server_number"],
                name="uniq_server_number_per_datacenter",
            )
        ]

    def __str__(self) -> str:
        return self.server_name


class HypervisorOS(models.Model):
    """
    One hypervisor/OS entry per reserved server (Step 2).
    """

    server = models.OneToOneField(
        ServerAllocation,
        on_delete=models.CASCADE,
        related_name="hypervisor_os",
    )

    hv_os_name = models.CharField(max_length=255)
    hypervisor_type_os_type = models.CharField(max_length=128)

    management_ip = models.GenericIPAddressField(protocol="IPv4")
    ports = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    version_build_number = models.CharField(max_length=128)

    license_key_status = models.CharField(max_length=128, null=True, blank=True)
    expiration_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["server__server_number"]

    def __str__(self) -> str:
        return self.hv_os_name


class VirtualMachine(models.Model):
    """
    Multiple logical VMs under a single hypervisor/OS (Step 3).
    """

    hypervisor = models.ForeignKey(
        HypervisorOS,
        on_delete=models.CASCADE,
        related_name="virtual_machines",
    )

    vm_name = models.CharField(max_length=255)
    management_ip = models.GenericIPAddressField(protocol="IPv4")

    sub_function_other = models.CharField(max_length=255, null=True, blank=True)
    software_vendor = models.CharField(max_length=255, null=True, blank=True)
    os = models.CharField(max_length=255, null=True, blank=True)

    activation_status = models.CharField(max_length=64, null=True, blank=True)
    license_subscription_status = models.CharField(
        max_length=128, null=True, blank=True
    )
    license_expiration_date = models.DateField(null=True, blank=True)

    application_name = models.CharField(max_length=255, null=True, blank=True)

    # Kept as strings to support Excel variations (ex: "2 vCPU-worker", etc.)
    vcpu_worker = models.CharField(max_length=128, null=True, blank=True)
    vramsize_gb = models.PositiveIntegerField(null=True, blank=True)
    storage_size_gb = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["hypervisor__server__server_number", "vm_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["hypervisor", "vm_name"],
                name="uniq_vm_name_per_hypervisor",
            )
        ]

    def __str__(self) -> str:
        return self.vm_name


class NetworkConfiguration(models.Model):
    """
    Network connectivity (uplinks) for a reserved server (Step 4).
    """

    server = models.ForeignKey(
        ServerAllocation,
        on_delete=models.CASCADE,
        related_name="network_configurations",
    )

    server_port_name = models.CharField(max_length=128)
    connection_type = models.CharField(max_length=64)
    network_role = models.CharField(max_length=64)

    uplink_hostname = models.CharField(max_length=255, null=True, blank=True)
    uplink_interface = models.CharField(max_length=128, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    lacp_group_port_channel_id = models.CharField(
        max_length=128, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["server__server_number", "server_port_name"]

    def __str__(self) -> str:
        return f"{self.server.server_name}:{self.server_port_name}"


class StorageConfiguration(models.Model):
    """
    Optional: if you later add a dedicated storage step or admin ingestion.

    Excel sheet `Storage` includes disk details per server.
    """

    server = models.ForeignKey(
        ServerAllocation,
        on_delete=models.CASCADE,
        related_name="storage_configurations",
    )

    disk_type = models.CharField(max_length=64, null=True, blank=True)
    disk_slot_no = models.PositiveIntegerField(null=True, blank=True)
    disk_size_gb = models.PositiveIntegerField(null=True, blank=True)
    raid_level_configuration = models.CharField(
        max_length=128, null=True, blank=True
    )
    usage_purpose = models.CharField(max_length=128, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["server__server_number", "disk_slot_no"]
