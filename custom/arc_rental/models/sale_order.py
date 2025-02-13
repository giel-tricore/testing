# -*- coding: utf-8 -*-
from odoo import fields, models, api
from math import ceil
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from pytz import timezone, UTC
from datetime import datetime, time
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    rental_time = fields.Many2many(
        'sale.temporal.recurrence', string='Rating time')
    rental_time_com = fields.Many2many(
        'sale.temporal.recurrence', 'wing_alternate_rent', string='Rating time', compute='compute_alternate_ids')

    _sql_constraints = [(
        'rental_period_coherence',
        "CHECK(rental_start_date <= rental_return_date)",
        "The rental start date must be before the rental return date if any.",
    )]

    def _rental_set_dates(self):
        super()._rental_set_dates()
        self.ensure_one()
        if self.rental_time:
            start = self.rental_time.rental_start_time
            end = self.rental_time.rental_end_time

            start_time = '{0:02.0f}:{1:02.0f}'.format(*divmod(start * 60, 60))
            end_time = '{0:02.0f}:{1:02.0f}'.format(*divmod(end * 60, 60))
            user_timezone = timezone(
                request.httprequest.cookies['tz'] or self.env.user.tz or 'UTC')
            
            utc_timezone = timezone('UTC')
            
            date_only = self.rental_start_date if self.rental_start_date else fields.Datetime.now()
            localized_datetime = utc_timezone.localize(date_only)
            date_only = localized_datetime.astimezone(user_timezone)
            date_only = date_only.date()


            user_time = datetime.strptime(start_time, "%H:%M").time()
            combined_datetime = datetime.combine(date_only, user_time)
            localized_datetime = user_timezone.localize(combined_datetime)
            start_date = localized_datetime.astimezone(UTC)

            user_time = datetime.strptime(end_time, "%H:%M").time()
            combined_datetime = datetime.combine(date_only, user_time)
            localized_datetime = user_timezone.localize(combined_datetime)
            return_date = localized_datetime.astimezone(UTC)
            

            self.update({
                'rental_start_date': start_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'rental_return_date': return_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            })

    @api.onchange('rental_time')
    def _onchange_rental_time(self):
        if len(self.rental_time) > 1:
            self.rental_time = self.rental_time[-1:]

    @api.depends('order_line')
    def compute_alternate_ids(self):
        for rec in self:
            rental_ids = []
            for line in rec.order_line:
                if line.product_template_id and line.product_template_id.product_pricing_ids:
                    for rental_time in line.product_template_id.product_pricing_ids:
                        rental_ids.append(rental_time.recurrence_id.id)
            if rental_ids:
                rec.rental_time_com = rental_ids
            else:
                rec.rental_time_com = self.env['sale.temporal.recurrence'].sudo().search([
                ]).ids

    def _cart_update(self, rental_time=False, *args, **kwargs):
        if rental_time:
            self.compute_alternate_ids()
            self.rental_time = [(6, 0, [int(rental_time)])]
        return super()._cart_update(*args, **kwargs)

    @api.onchange('rental_start_date', 'rental_time')
    def _onchange_duration_show_update_duration(self):
        self.show_update_duration = any(
            line.is_rental for line in self.order_line)

    @api.onchange('rental_start_date')
    def _onchange_rental_start_date(self):
        for rec in self:
            if rec.rental_start_date:
                start_date = fields.Datetime.from_string(rec.rental_start_date)
                return_date = start_date + timedelta(hours=1)
                rec.rental_return_date = fields.Datetime.to_string(return_date)
                rec.rental_return_date = return_date

    @api.depends('rental_start_date', 'rental_return_date', 'rental_time')
    def _compute_duration(self):
        rental_time_obj = self.filtered('rental_time')
        super_call_obj = self - rental_time_obj
        if super_call_obj:
            super(SaleOrderInherit, super_call_obj)._compute_duration()
        rental_time_obj.duration_days = 0
        rental_time_obj.remaining_hours = 0
        for order in rental_time_obj or []:
            if order.rental_start_date and order.rental_return_date and order.order_line:
                pricing = order.order_line[0].product_id._get_best_pricing_rule(
                    start_date=order.rental_start_date, end_date=order.rental_return_date, rental_time=order.rental_time
                )
                duration = pricing.recurrence_id._get_custom_renting_duration(
                    order.rental_start_date, order.rental_return_date) or 0
                order.remaining_hours = ceil(duration)
                order.duration_days = 0
