# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from math import ceil
from pytz import timezone, UTC
from copy import copy
import json
from pytz import timezone, UTC
from datetime import datetime, time
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import format_amount

from odoo.addons.sale_renting.models.product_pricing import PERIOD_RATIO


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def getDateInfo(self):
        rent_order = self.env['sale.order'].sudo().search([
            ('is_rental_order', '=', True),
            ('state', 'not in', ('draft', 'cancel')),
            ('order_line.product_id.product_tmpl_id', '=', self.id),
        ])
        order_details = {}
        default_slot = {}
        date_wise_slot = {}

        final_data = {}
        for slot in self.product_pricing_ids:
            if slot.recurrence_id.rental_time in default_slot:
                default_slot[slot.recurrence_id.rental_time] += 1
            else:
                default_slot[slot.recurrence_id.rental_time] = 1

        for order in rent_order:
            od_date = order.rental_start_date
            client_tz = timezone(request.httprequest.cookies['tz'])
            od_date = od_date.astimezone(client_tz)
            slot_id = order.rental_time.rental_time

            od_str_date = od_date.strftime("%Y-%m-%d")

            if od_str_date in final_data:
                if slot_id == "fullday":
                    final_data[od_str_date] = "red"
                if slot_id in final_data[od_str_date]:
                    final_data[od_str_date][slot_id] += 1
                else:
                    final_data[od_str_date][slot_id] = 1
            else:
                final_data[od_str_date] = {}
                final_data[od_str_date][slot_id] = 1

        result_data = {}
        for date in final_data:
            for slot in default_slot:
                if slot in final_data[date] and slot == "fullday":
                    result_data[date] = "red"
                    break
                elif slot in final_data[date] and date in result_data:
                    result_data[date] = "red"
                    break
                elif slot in final_data[date]:
                    result_data[date] = "yellow"

        return str(json.dumps(result_data))

    def _get_best_pricing_rule(self, product=False, start_date=False, end_date=False, **kwargs):
        res = super()._get_best_pricing_rule(product=product,
                                             start_date=start_date, end_date=end_date, **kwargs)
        if kwargs.get('rental_time'):
            rental_time = kwargs.get('rental_time')
            self.ensure_one()
            best_pricing_rule = self.env['product.pricing']
            if not self.product_pricing_ids or not (start_date and end_date):
                return best_pricing_rule
            pricelist = kwargs.get('pricelist', self.env['product.pricelist'])
            currency = kwargs.get('currency', self.currency_id)
            company = kwargs.get('company', self.env.company)
            duration_dict = self.env['product.pricing']._compute_duration_vals(
                start_date, end_date)
            min_price = float("inf")
            available_pricings = self.env['product.pricing'].search([])
            available_pricings = available_pricings.filtered(
                lambda pricing: pricing.recurrence_id.id == int(rental_time))
            for pricing in available_pricings:
                unit = pricing.recurrence_id.unit
                price = pricing._compute_price(duration_dict[unit], unit)
                if pricing.currency_id != currency:
                    price = pricing.currency_id._convert(
                        from_amount=price,
                        to_currency=currency,
                        company=company,
                        date=fields.Date.today(),
                    )
                if price < min_price:
                    min_price, best_pricing_rule = price, pricing
            return best_pricing_rule
        return res

    def _get_additionnal_combination_info(self, product_or_template, quantity, date, website):
        res = super()._get_additionnal_combination_info(
            product_or_template, quantity, date, website)
        if not product_or_template.rent_ok:
            return res

        currency = website.currency_id
        pricelist = website.pricelist_id
        ProductPricing = self.env['product.pricing']

        pricing = ProductPricing._get_first_suitable_pricing(
            product_or_template, pricelist)
        if not pricing:
            return res

        # Compute best pricing rule or set default
        order = website.sale_get_order(
        ) if website and request else self.env['sale.order']

        start_date = self.env.context.get(
            'start_date') or order.rental_start_date
        end_date = self.env.context.get(
            'start_date') or order.rental_start_date
        rental_time = self.env.context.get('rental_time') or order.rental_time
        if start_date and end_date:
            current_pricing = product_or_template._get_best_pricing_rule(
                start_date=start_date,
                end_date=end_date,
                pricelist=pricelist,
                currency=currency,
                rental_time=rental_time
            )
            current_unit = current_pricing.recurrence_id.unit
            if not rental_time:
                current_duration = ProductPricing._compute_duration_vals(
                    start_date, end_date
                )[current_unit]
            else:
                current_duration = current_pricing.recurrence_id._get_custom_renting_duration(
                    start_date, end_date)
        else:
            current_unit = pricing.recurrence_id.unit
            current_duration = pricing.recurrence_id.duration
            current_pricing = pricing

        # Compute current price

        # Here we don't add the current_attributes_price_extra nor the
        # no_variant_attributes_price_extra to the context since those prices are not added
        # in the context of rental.
        current_price = pricelist._get_product_price(
            product=product_or_template,
            quantity=quantity,
            currency=currency,
            start_date=start_date,
            end_date=end_date,
            rental_time=rental_time
        )
        default_start_date, default_end_date = self._get_default_renting_dates(
            start_date, end_date, current_duration, current_unit
        )
        ratio = ceil(current_duration) / \
            pricing.recurrence_id.duration if pricing.recurrence_id.duration else 1
        if current_unit != pricing.recurrence_id.unit:
            ratio *= PERIOD_RATIO[current_unit] / \
                PERIOD_RATIO[pricing.recurrence_id.unit]

        # apply taxes
        product_taxes = res['product_taxes']
        if product_taxes:
            current_price = self.env['product.template']._apply_taxes_to_price(
                current_price, currency, product_taxes, res['taxes'], product_or_template,
            )

        suitable_pricings = ProductPricing._get_suitable_pricings(
            product_or_template, pricelist)

        # If there are multiple pricings with the same recurrence, we only keep the cheapest ones
        best_pricings = {}
        for p in suitable_pricings:
            if p.recurrence_id not in best_pricings:
                best_pricings[p.recurrence_id] = p
            elif best_pricings[p.recurrence_id].price > p.price:
                best_pricings[p.recurrence_id] = p

        suitable_pricings = best_pricings.values()

        def _pricing_price(pricing):
            if product_taxes:
                price = self.env['product.template']._apply_taxes_to_price(
                    pricing.price, currency, product_taxes, res['taxes'], product_or_template
                )
            else:
                price = pricing.price
            if pricing.currency_id == currency:
                return price
            return pricing.currency_id._convert(
                from_amount=price,
                to_currency=currency,
                company=self.env.company,
                date=date,
            )
        pricing_table = [
            (p.name, format_amount(self.env, _pricing_price(p), currency))
            for p in suitable_pricings
        ]
        recurrence = pricing.recurrence_id
        booked_slot = []
        unbooked_slot = []
        booked_slot_ids = []
        all_slots = []

        rental_time = request.env['sale.temporal.recurrence'].sudo().browse(int(rental_time))
        user_timezone = timezone(
            request.httprequest.cookies['tz'] or self.env.user.tz or 'UTC')
        
        utc_timezone = timezone('UTC')

        localized_datetime = start_date or fields.Datetime.now()
        # localized_datetime = utc_timezone.localize(date_only)
        date_only = localized_datetime.astimezone(user_timezone)
        date_only = date_only.date()

        start = rental_time.rental_start_time
        end = rental_time.rental_end_time

        # start_time = '{0:02.0f}:{1:02.0f}'.format(*divmod(start * 60, 60))
        # end_time = '{0:02.0f}:{1:02.0f}'.format(*divmod(end * 60, 60))

        start_time = '00:00'
        end_time = '23:59'

        user_time = datetime.strptime(start_time, "%H:%M").time()
        combined_datetime = datetime.combine(date_only, user_time)
        localized_datetime = user_timezone.localize(combined_datetime)
        start_date = localized_datetime.astimezone(UTC)

        user_time = datetime.strptime(end_time, "%H:%M").time()
        combined_datetime = datetime.combine(date_only, user_time)
        localized_datetime = user_timezone.localize(combined_datetime)
        end_date = localized_datetime.astimezone(UTC)

        for pr in self.product_pricing_ids:
            all_slots.append(pr.recurrence_id.id)

            rent_order = self.env['sale.order'].sudo().search([
                ('is_rental_order', '=', True),
                ('state', 'not in', ('draft', 'cancel')),
                ('rental_start_date', '>=', start_date),
                ('rental_start_date', '<=', end_date),
                ('order_line.product_id.product_tmpl_id', '=', self.id),
                ('rental_time.id', 'in', [pr.recurrence_id.id]),
            ])
            if rent_order:
                booked_slot.append([
                    pr.recurrence_id.rental_start_time,
                    pr.recurrence_id.rental_end_time,
                    pr.recurrence_id.id
                ])
                booked_slot_ids.append(pr.recurrence_id.id)
            else:
                unbooked_slot.append([
                    pr.recurrence_id.rental_start_time,
                    pr.recurrence_id.rental_end_time,
                    pr.recurrence_id.id
                ])

        for slot in unbooked_slot:
            booked = False
            for b_slot in booked_slot:
                if slot[0] <= b_slot[0] and slot[1] <= b_slot[0]:
                    booked = False
                elif slot[0] >= b_slot[1] and slot[1] >= b_slot[1]:
                    booked = False
                else:
                    booked = True
                    break
            if booked:
                booked_slot_ids.append(slot[2])

        return {
            **res,
            'is_rental': True,
            'rental_duration': recurrence.duration,
            'rental_duration_unit': recurrence.unit,
            'rental_unit': recurrence._get_unit_label(recurrence.duration),
            'default_start_date': default_start_date,
            'default_end_date': default_end_date,
            'current_rental_duration': ceil(current_duration),
            'current_rental_unit': current_pricing.recurrence_id._get_unit_label(current_duration),
            'current_rental_price': current_price,
            'current_rental_price_per_unit': current_price / (ratio or 1),
            'base_unit_price': 0,
            'base_unit_name': False,
            'pricing_table': pricing_table,

            'booked_slot': booked_slot_ids,
            'all_slots': all_slots,
            'prevent_zero_price_sale': False,
        }

    @api.model
    def _get_default_renting_dates(self, start_date, end_date, duration, unit):
        """ Get default renting dates to help user

        :param datetime start_date: a start_date which is directly returned if defined
        :param datetime end_date: a end_date which is directly returned if defined
        :param int duration: the duration expressed in int, in the unit given
        :param string unit: The duration unit, which can be 'hour', 'day', 'week' or 'month'
        """
        if start_date and end_date and start_date > end_date:
            raise UserError(
                _("Please choose a return date that is after the pickup date."))

        if start_date or end_date:
            return start_date, end_date

        default_start_dt = self._get_default_start_date()
        if unit == 'hour':
            default_end_dt = self._get_default_end_date(
                default_start_dt, duration, unit)
        else:
            default_start_dt = datetime.combine(
                default_start_dt.date(), datetime.min.time())
            default_end_dt = self._get_default_end_date(
                default_start_dt + relativedelta(seconds=-1), duration, unit)
            # Consider the timezone if frontend request
            # Return the UTC value according to the client
            # because the frontend will convert values according to its timezone
            # (and without conversion, we risk changing day).
            if request and request.is_frontend and request.httprequest.cookies.get('tz'):
                client_tz = timezone(request.httprequest.cookies['tz'])
                default_start_dt = client_tz.localize(
                    default_start_dt).astimezone(UTC)
                default_end_dt = client_tz.localize(
                    default_end_dt).astimezone(UTC)
        return default_start_dt, default_end_dt

    @api.model
    def _get_default_start_date(self):
        """ Get the default pickup date and make it extensible """
        return self._get_first_potential_date(
            fields.Datetime.now() + relativedelta(days=1, minute=0, second=0, microsecond=0)
        )

    @api.model
    def _get_default_end_date(self, start_date, duration, unit):
        """ Get the default return date based on pickup date and duration

        :param datetime start_date: the default start_date
        :param int duration: the duration expressed in int, in the unit given
        :param string unit: The duration unit, which can be 'hour', 'day', 'week' or 'month'
        """
        return self._get_first_potential_date(max(
            start_date + relativedelta(**{f'{unit}s': duration}),
            start_date + self.env.company._get_minimal_rental_duration()
        ))

    @api.model
    def _get_first_potential_date(self, date):
        """ Get the first potential date which respects company unavailability days settings
        """
        days_forbidden = self.env.company._get_renting_forbidden_days()
        weekday = date.isoweekday()
        for i in range(7):
            if ((weekday + i) % 7 or 7) not in days_forbidden:
                break
        return date + relativedelta(days=i)

    def _search_render_results_prices(self, mapping, combination_info):
        if not combination_info.get('is_rental'):
            return super()._search_render_results_prices(mapping, combination_info)

        return self.env['ir.ui.view']._render_template(
            'website_sale_renting.rental_search_result_price',
            values={
                'currency': mapping['detail']['display_currency'],
                'price': combination_info['price'],
                'duration': combination_info['rental_duration'],
                'unit': combination_info['rental_unit'],
            }
        ), None

    def _get_sales_prices(self, pricelist, fiscal_position):
        prices = super()._get_sales_prices(pricelist, fiscal_position)

        for template in self:
            if not template.rent_ok:
                continue
            pricing = self.env['product.pricing']._get_first_suitable_pricing(
                template, pricelist)
            if pricing:
                recurrence = pricing.recurrence_id
                prices[template.id]['rental_duration'] = recurrence.duration
                prices[template.id]['rental_unit'] = recurrence._get_unit_label(
                    recurrence.duration)
            else:
                prices[template.id]['rental_duration'] = 0
                prices[template.id]['rental_unit'] = False

        return prices

    def _search_get_detail(self, website, order, options):
        search_details = super()._search_get_detail(website, order, options)
        if options.get('rent_only') or (options.get('from_date') and options.get('to_date')):
            search_details['base_domain'].append([('rent_ok', '=', True)])
        return search_details

    def _can_be_added_to_cart(self):
        """Override to allow rental products to be used in a sale order"""
        return super()._can_be_added_to_cart() or self.rent_ok

    def _website_show_quick_add(self):
        self.ensure_one()
        website = self.env['website'].get_current_website()
        return super()._website_show_quick_add() or (
            self.rent_ok and (
                not website.prevent_zero_price_sale or self._get_contextual_price())
        )
