# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ProductPricing(models.Model):
    _inherit = 'product.pricing'

    @api.model
    def _compute_duration_vals(self, start_date, end_date):
        duration = end_date - start_date
        vals = dict(hour=((duration.days + 1) * 24 + duration.seconds / 3600))
        vals['day'] = math.ceil(vals['hour'] / 24)
        vals['week'] = math.ceil(vals['day'] / 7)
        duration_diff = relativedelta(end_date, start_date)
        months = 1 if duration_diff.days or duration_diff.hours or duration_diff.minutes else 0
        months += duration_diff.months
        months += duration_diff.years * 12
        vals['month'] = months
        vals['year'] = months/12
        return vals