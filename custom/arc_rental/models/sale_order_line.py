# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pytz import timezone, UTC
from odoo.http import request
from odoo import _, api, fields, models
from odoo.fields import Command
from datetime import datetime, timedelta


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    rental_time = fields.Many2many(
        'sale.temporal.recurrence', related="order_id.rental_time", string='Rating time')

    def _get_rental_pricing_description(self):
        self.ensure_one()
        if self.is_rental:
            order = self.order_id
            pricing = self.product_id._get_best_pricing_rule(
                start_date=order.rental_start_date,
                end_date=order.rental_return_date,
                pricelist=order.pricelist_id,
                company=order.company_id,
                currency=order.currency_id,
                rental_time=self.rental_time,
            )
            return pricing.description
        return super()._get_rental_pricing_description()

    def _get_pricelist_price(self):
        self.ensure_one()
        if self.is_rental:
            self.order_id._rental_set_dates()
            return self.order_id.pricelist_id._get_product_price(
                self.product_id.with_context(
                    **self._get_product_price_context()),
                self.product_uom_qty or 1.0,
                currency=self.currency_id,
                uom=self.product_uom,
                date=self.order_id.date_order or fields.Date.today(),
                start_date=self.start_date,
                end_date=self.return_date,
                rental_time=self.rental_time,
            )
        return super()._get_pricelist_price()

    

    def get_description_following_lines(self):
        if self.order_id.is_rental_order:
            client_tz = timezone(request.httprequest.cookies['tz'] or self.env.user.tz or 'UTC')
            od_date = self.order_id.rental_start_date.astimezone(client_tz)
            od_date = od_date.strftime("%m/%d/%Y")

            final_start_time = self.order_id.rental_time.rental_start_time
            time_start = '{0:02.0f}:{1:02.0f}'.format(*divmod(final_start_time * 60, 60))
            start_time = datetime.strptime(time_start, "%H:%M")
            
            final_end_time = self.order_id.rental_time.rental_end_time
            time_end = '{0:02.0f}:{1:02.0f}'.format(*divmod(final_end_time * 60, 60))
            end_time = datetime.strptime(time_end, "%H:%M")

            return [od_date + " " + str(start_time.time()) + " to " + str(end_time.time())]
        else:
            return self.name.splitlines()[1:]
