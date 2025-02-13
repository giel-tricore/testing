from odoo import _, api, fields, models
from datetime import datetime, timedelta
from pytz import timezone, UTC
from odoo.exceptions import UserError, ValidationError
from odoo.http import request


class SaleTemporalRecurrence(models.Model):
    _inherit = 'sale.temporal.recurrence'

    rental_time = fields.Selection(
        selection=[
            ('morning', 'Morning'),
            ('afternoon', 'Afternoon'),
            ('fullday', 'Full Day'),
        ],
        string="Rental Time",
        store=True)
    rental_start_time = fields.Float(string="Rental Start Date")
    rental_end_time = fields.Float(string="Rental Return Date")
    duration = fields.Integer(
        required=True,
        default=1,
        help="Minimum duration before this rule is applied. If set to 0, it represents a fixed"
        "rental price.",
        compute="_compute_duration_time",
        compute_sudo=True
        )

    @api.depends('rental_start_time', 'rental_end_time')
    def _compute_duration_time(self):
        for rec in self:
            start = rec.rental_start_time
            end = rec.rental_end_time

            start_time = '{0:02.0f}:{1:02.0f}'.format(*divmod(start * 60, 60))
            end_time = '{0:02.0f}:{1:02.0f}'.format(*divmod(end * 60, 60))

            if end_time < start_time and end_time != '00:00':
                raise ValidationError(
                    _("Please fill up start time less than end time."))

            start_time = datetime.strptime(start_time, "%H:%M")
            end_time = datetime.strptime(end_time, "%H:%M")

            delta = end_time - start_time
            hours = delta.total_seconds() / 3600
            if hours:
                rec.sudo().write({'duration': int(hours)})
            else:
                rec.sudo().write({'duration': 0})

    @api.constrains('rental_time', 'unit')
    def _check_rental_time_unit(self):
        for record in self:
            if record.rental_time and record.unit != 'hour':
                raise UserError(
                    "If Rental Time is set, the Unit must be 'Hour'."
                )

    @api.model
    def _get_custom_renting_duration(self, start_date, end_date):
        client_tz = timezone(
            request.httprequest.cookies['tz'] or self.env.user.tz or 'UTC')
        start_date = client_tz.localize(start_date).astimezone(UTC)
        end_date = client_tz.localize(end_date).astimezone(UTC)
        daily_limit_hours = self.duration
        total_days = (end_date - start_date).days
        full_days = max(0, total_days+1)
        return full_days * daily_limit_hours
