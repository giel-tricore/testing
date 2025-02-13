# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

class Pricelist(models.Model):
    _inherit = "product.pricelist"

    def _compute_price_rule(
        self, products, quantity, currency=None, date=False, start_date=None, end_date=None,
        **kwargs
    ):
        if not kwargs.get('rental_time'):
            return super()._compute_price_rule(products, quantity, currency, date, **kwargs)

        rental_time = kwargs.get('rental_time')
        self and self.ensure_one()  # self is at most one record

        currency = currency or self.currency_id or self.env.company.currency_id
        currency.ensure_one()

        if not products:
            return {}

        if not date:
            # Used to fetch pricelist rules and currency rates
            date = fields.Datetime.now()

        results = {}

        rental_products = products.filtered('rent_ok')
        Pricing = self.env['product.pricing']
        for product in rental_products:
            if start_date and end_date:
                pricing = product._get_best_pricing_rule(
                    start_date=start_date, end_date=end_date, pricelist=self, currency=currency, rental_time = rental_time
                )
                duration = pricing.recurrence_id._get_custom_renting_duration(start_date, end_date) or 0
            else:
                pricing = Pricing._get_first_suitable_pricing(product, self)
                duration = pricing.recurrence_id.duration

            if pricing:
                price = pricing._compute_price(duration, pricing.recurrence_id.unit)
            elif product._name == 'product.product':
                price = product.lst_price
            else:
                price = product.list_price
            results[product.id] = pricing.currency_id._convert(
                price, currency, self.env.company, date
            ), False

        price_computed_products = self.env[products._name].browse(results.keys())
        return {
            **results,
            **super()._compute_price_rule(
                products - price_computed_products, quantity, currency=currency, date=date, **kwargs
            ),
        }
