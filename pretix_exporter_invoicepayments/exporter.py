from collections import OrderedDict
from decimal import Decimal

import dateutil
import pytz
from dateutil.parser import parse
from django import forms
from django.db.models import Subquery, OuterRef
from django.db.models.functions import TruncDay, TruncDate
from django.utils.formats import date_format
from django.utils.translation import gettext as _

from pretix.base.exporter import ListExporter
from pretix.base.models import Invoice, OrderPayment, OrderRefund, InvoiceLine, GiftCard
from pretix.control.forms.filter import get_all_payment_providers


class InvoicePaymentsReport(ListExporter):
    identifier = 'invoice_payments'
    verbose_name = _('Invoices and payments')

    @property
    def additional_form_fields(self) -> dict:
        return OrderedDict(
            [
                ('date_from',
                 forms.DateField(
                     label=_('Start date'),
                     widget=forms.DateInput(attrs={'class': 'datepickerfield'}),
                     required=False,
                 )),
                ('date_to',
                 forms.DateField(
                     label=_('End date'),
                     widget=forms.DateInput(attrs={'class': 'datepickerfield'}),
                     required=False,
                 )),
            ]
        )

    def iterate_list(self, form_data):
        if self.events.first():
            self.tz = self.events.first().timezone
        else:
            self.tz = pytz.UTC

        date_from, date_to = None, None
        if form_data.get('date_from'):
            date_from = form_data.get('date_from')
            if isinstance(date_from, str):
                date_from = dateutil.parser.parse(date_from).date()
        if form_data.get('date_to'):
            date_to = form_data.get('date_to')
            if isinstance(date_to, str):
                date_to = dateutil.parser.parse(date_to).date()

        invoice_qs = InvoiceLine.objects.filter(
            invoice__event__in=self.events
        ).select_related('invoice', 'invoice__order', 'invoice__refers')
        payment_qs = OrderPayment.objects.filter(
            order__event__in=self.events,
            state__in=(OrderPayment.PAYMENT_STATE_CONFIRMED, OrderPayment.PAYMENT_STATE_REFUNDED),
        ).annotate(
            date=TruncDate('payment_date', tzinfo=self.tz),
            last_invoice_number=Subquery(
                Invoice.objects.filter(
                    order=OuterRef('order'),
                ).values('full_invoice_no').order_by('-date', '-invoice_no')[:1]
            )
        ).select_related('order')
        refund_qs = OrderRefund.objects.filter(
            order__event__in=self.events,
            state__in=(OrderRefund.REFUND_STATE_DONE,),
        ).annotate(
            date=TruncDate('execution_date', tzinfo=self.tz),
            last_invoice_number=Subquery(
                Invoice.objects.filter(
                    order=OuterRef('order'),
                ).values('full_invoice_no').order_by('-date', '-invoice_no')[:1]
            )
        ).select_related('order')

        if date_from:
            invoice_qs = invoice_qs.filter(invoice__date__gte=date_from)
            payment_qs = payment_qs.filter(date__gte=date_from)
            refund_qs = refund_qs.filter(date__gte=date_from)

        if date_to:
            invoice_qs = invoice_qs.filter(invoice__date__lte=date_to)
            payment_qs = payment_qs.filter(date__lte=date_to)
            refund_qs = refund_qs.filter(date__lte=date_to)

        yield [
            _('Invoice number'),
            _('Line number'),
            _('Description'),
            _('Gross price'),
            _('Net price'),
            _('Tax'),
            _('Tax rate'),
            _('Tax name'),
            _('Date'),
            _('Order code'),
            _('Type'),
            _('Cancellation of'),
            _('Gift card created in'),
        ]
        pprovs = dict(get_all_payment_providers())

        for i in invoice_qs:
            yield [
                i.invoice.full_invoice_no,
                i.position,
                i.description,
                i.gross_value,
                i.net_value,
                i.tax_value,
                i.tax_rate,
                i.tax_name,
                i.invoice.date,
                i.invoice.order.code,
                _('Invoice'),
                i.invoice.refers.full_invoice_no if i.invoice.refers else '',
                ''
            ]

        for p in payment_qs:
            gci = ''
            if p.provider == 'giftcard':
                if 'gift_card' in p.info_data:
                    gc = GiftCard.objects.get(pk=p.info_data.get('gift_card'))
                    order = gc.transactions.first().order
                    if order:
                        inv = order.invoices.last()
                        if inv:
                            gci = inv.full_invoice_no

            yield [
                p.last_invoice_number,
                '',
                _('Gift card') if p.provider == 'giftcard' else _('Payment'),
                p.amount * Decimal('-1.00'),
                '',
                '',
                '',
                '',
                p.payment_date,
                p.order.code,
                str(pprovs[p.provider]),
                '',
                gci
            ]

        for p in refund_qs:
            gci = ''
            if p.provider == 'giftcard':
                if 'gift_card' in p.info_data:
                    gc = GiftCard.objects.get(pk=p.info_data.get('gift_card'))
                    order = gc.transactions.first().order
                    if order:
                        inv = order.invoices.last()
                        if inv:
                            gci = inv.full_invoice_no

            yield [
                p.last_invoice_number,
                '',
                _('Gift card') if p.provider == 'giftcard' else _('Refund'),
                p.amount,
                '',
                '',
                '',
                '',
                p.execution_date,
                p.order.code,
                str(pprovs[p.provider]),
                '',
                gci
            ]
