# Register your receivers here
from django.dispatch import receiver

from pretix.base.signals import register_data_exporters


@receiver(register_data_exporters, dispatch_uid="exporter_invoicepayments_exp1")
def register_export1(sender, **kwargs):
    from .exporter import InvoicePaymentsReport
    return InvoicePaymentsReport
