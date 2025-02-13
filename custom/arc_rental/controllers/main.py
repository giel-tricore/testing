# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields

from odoo.http import request, route
from calendar import monthrange
from odoo.addons.website_sale.controllers.main import WebsiteSale
from datetime import datetime, timedelta
from pytz import timezone, UTC


def get_dates_by_month_and_week(start_year, start_month, date_ranges):
    """
    Organize date ranges into months and weeks based on the start month and year.
    :param start_month: The starting month (integer).
    :param start_year: The starting year (integer).
    :param date_ranges: List of dictionaries with "start" and "end" keys.
    :return: Nested list [[weeks for month 1], [weeks for month 2], ...].
    """
    # Parse the input date ranges
    parsed_ranges = [
        {
            "start": datetime.strptime(item["start"], "%Y-%m-%d").date(),
            "end": datetime.strptime(item["end"], "%Y-%m-%d").date(),
        }
        for item in date_ranges
    ]

    # Prepare the result structure
    result = []

    # Process two consecutive months
    for month_offset in range(2):
        month = start_month + month_offset
        year = start_year
        if month > 12:  # Handle year transition
            month -= 12
            year += 1

        # Get the number of days in the current month
        _, days_in_month = monthrange(year, month)

        # Initialize weekly structure for the month
        weeks = [[] for _ in range(5)]  # Assuming a max of 5 weeks in a month

        # Populate weeks with dates from ranges
        for date_range in parsed_ranges:
            current_start = max(
                date_range["start"], datetime(year, month, 1).date())
            current_end = min(date_range["end"], datetime(
                year, month, days_in_month).date())

            # Skip if range does not overlap with the current month
            if current_start > current_end:
                continue

            # Add dates to the appropriate week
            date = current_start
            while date <= current_end:
                # Determine the week index (0-based)
                week_index = (date.day - 1) // 7
                weeks[week_index].append(date.strftime("%Y-%m-%d"))
                date += timedelta(days=1)

        result.append(weeks)

    return result


def get_all_dates_as_list(start_year, start_month, date_ranges):
    """
    Flatten and return all dates from the ranges as a single list.
    :param start_month: Starting month (integer).
    :param start_year: Starting year (integer).
    :param date_ranges: List of dictionaries with "start" and "end" keys.
    :return: Flat list of all dates in "YYYY-MM-DD" format.
    """
    # Parse the input date ranges
    parsed_ranges = [
        {
            "start": datetime.strptime(item["start"], "%Y-%m-%d").date(),
            "end": datetime.strptime(item["end"], "%Y-%m-%d").date(),
        }
        for item in date_ranges
    ]

    # Collect all dates in a flat list
    all_dates = []

    # Process two consecutive months
    for month_offset in range(2):
        month = start_month + month_offset
        year = start_year
        if month > 12:  # Handle year transition
            month -= 12
            year += 1

        # Get the number of days in the current month
        _, days_in_month = monthrange(year, month)

        # Collect dates for each range
        for date_range in parsed_ranges:
            current_start = max(
                date_range["start"], datetime(year, month, 1).date())
            current_end = min(date_range["end"], datetime(
                year, month, days_in_month).date())

            # Skip if range does not overlap with the current month
            if current_start > current_end:
                continue

            # Add dates to the flat list
            date = current_start
            while date <= current_end:
                all_dates.append(date.strftime("%Y-%m-%d"))
                date += timedelta(days=1)

    return all_dates


class WebsiteSaleRenting(WebsiteSale):

    @route('/arc_rental/disable_days', type='json', auth="public", methods=['POST'], website=True)
    def arc_rental_disable_days(self, start_month=None, start_year=None, rental_time=None, product_id=False, additionalMonth=False, **kw):
        if not start_month or not start_year or not rental_time:
            return []

        start_date = datetime(start_year, start_month, 1)
        end_month = start_month
        if additionalMonth:
            end_month += 1
        _, days_in_month = monthrange(start_year, end_month)
        end_date = datetime(start_year, end_month, days_in_month)
        client_tz = timezone(
            request.httprequest.cookies['tz'] or self.env.user.tz or 'UTC')
        start_date = client_tz.localize(start_date).astimezone(UTC)
        end_date = client_tz.localize(end_date).astimezone(UTC)
        if product_id:
            product_id = int(product_id)
        else:
            order_sudo = request.website.sale_get_order()
            if not order_sudo or not order_sudo.order_line:
                return []

            product_id = order_sudo.order_line[0].product_id.id

        if rental_time != 'fullday':
            rental_orders = request.env['sale.order'].sudo().search([
                ('is_rental_order', '=', True),
                ('state', 'not in', ('draft', 'cancel')),
                ('rental_start_date', '>=', start_date),
                ('rental_start_date', '<=', end_date),
                ('order_line.product_id', '=', product_id),
                '|', ('rental_time', '=', 'fullday'),
                ('rental_time', '=', rental_time),
            ], order='rental_start_date,duration_days desc')
        else:
            rental_orders = request.env['sale.order'].sudo().search([
                ('is_rental_order', '=', True),
                ('state', 'not in', ('draft', 'cancel')),
                ('rental_start_date', '>=', start_date),
                ('rental_start_date', '<=', end_date),
                ('order_line.product_id', '=', product_id),
                ('rental_time', '!=', False),
            ], order='rental_start_date,duration_days desc')

        if rental_orders:
            disabled_days = []
            last_start = False
            last_end = False
            for order in rental_orders:
                client_tz = timezone(
                    request.httprequest.cookies['tz'] or self.env.user.tz or 'UTC')
                start_date = UTC.localize(
                    order.rental_start_date).astimezone(client_tz)
                end_date = UTC.localize(
                    order.rental_return_date).astimezone(client_tz)
                if not last_end or not (start_date > last_start and end_date < last_end):
                    disabled_days.append({
                        'start': start_date.strftime('%Y-%m-%d'),
                        'end': end_date.strftime('%Y-%m-%d'),
                    })

            # datas = get_dates_by_month_and_week(start_year, start_month, disabled_days)
            datas = get_all_dates_as_list(
                start_year, start_month, disabled_days)

            return datas

        return []

    @route('/shop/cart/update_rental_time', type='json', auth="public", methods=['POST'], website=True)
    def cart_update_rental_time(self, rental_time=None, is_from_product_page=False):
        order_sudo = request.website.sale_get_order()
        if order_sudo and not is_from_product_page:
            order_sudo.rental_time = rental_time
            order_sudo._recompute_rental_prices()

        values = {}
        values['cart_ready'] = order_sudo._is_cart_ready()
        values['website_sale.cart_lines'] = request.env['ir.ui.view']._render_template(
            'website_sale.cart_lines', {
                'website_sale_order': order_sudo,
                'date': fields.Date.today(),
                'suggested_products': order_sudo._cart_accessories(),
            }
        )
        values['website_sale.total'] = request.env['ir.ui.view']._render_template(
            'website_sale.total', {
                'website_sale_order': order_sudo,
            }
        )
        return {
            'rental_time': rental_time,
            'values': values,
        }

    def _shop_get_query_url_kwargs(self, category, search, min_price, max_price, **post):
        result = super()._shop_get_query_url_kwargs(
            category, search, min_price, max_price, **post)
        result.update(
            rental_time=post.get('rental_time'),
        )
        return result

    def _product_get_query_url_kwargs(self, category, search, **kwargs):
        result = super()._product_get_query_url_kwargs(category, search, **kwargs)
        result.update(
            rental_time=kwargs.get('rental_time'),
        )
        return result

    def _prepare_product_values(self, product, category, search, **kwargs):
        result = super()._prepare_product_values(product, category, search, **kwargs)
        if kwargs.get('rental_time'):
            result.update(
                rental_time=kwargs.get('rental_time'),
            )
        return result

    def _get_cart_notification_information(self, order, line_ids):
        order.action_update_rental_prices()
        return super()._get_cart_notification_information(order, line_ids)
