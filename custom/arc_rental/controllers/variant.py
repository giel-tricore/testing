# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.http import request, route

from odoo.addons.website_sale.controllers.variant import WebsiteSaleVariantController


class WebsiteSaleRentingVariantController(WebsiteSaleVariantController):

    @route()
    def get_combination_info_website(self, *args, rental_time=None, **kwargs):
        """ Override to parse and add to context optional pickup and return dates."""
        if rental_time:
            request.update_context(rental_time=rental_time)
        return super().get_combination_info_website(
            *args, rental_time=None, **kwargs
        )
