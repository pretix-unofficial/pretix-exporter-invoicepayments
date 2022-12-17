from django.utils.translation import gettext_lazy
from . import __version__

try:
    from pretix.base.plugins import PluginConfig
except ImportError:
    raise RuntimeError("Please use pretix 2.7 or above to run this plugin!")


class PluginApp(PluginConfig):
    name = "pretix_exporter_invoicepayments"
    verbose_name = "Invoice & Payment exporter"

    class PretixPluginMeta:
        name = gettext_lazy("Invoice & Payment exporter")
        author = "pretix team"
        description = gettext_lazy("Export payments and invoices in the same sheet")
        visible = True
        version = __version__
        category = "FORMAT"
        compatibility = "pretix>=3.10.0"

    def ready(self):
        from . import signals  # NOQA


