/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { WebsiteSale } from '@website_sale/js/website_sale';
import wSaleUtils from "@website_sale/js/website_sale_utils";
import '@website_sale_renting/js/variant_mixin';
import { deserializeDateTime } from "@web/core/l10n/dates";


const { DateTime } = luxon;

publicWidget.registry.WebsiteSaleDaterangePicker.include({

    _isValidDate(date) {
        return !this.rentingUnavailabilityDays[date.weekday];
    },
    _isHighlightDate(date) {
        let date_info=$('.get_date_info').data('date_info')
        const dt=date.toISODate()
        if(date_info.hasOwnProperty(dt)){
            if(date_info[dt] == 'yellow'){
                return 'yellow'
            }
            if(date_info[dt] == 'red'){
                return 'red'
            }
        }
    },
    
    _initSaleRentingDateRangePicker(el) {
        const value = this.startDate ? [this.startDate] : [""];
        //const value = DateTime.now()
        this.call(
            "datetime_picker",
            "create",
            {
                target: el,
                pickerProps: {
                    value,
                    range: false,
                    type: "date",
                    minDate: DateTime.now(),
                    maxDate: DateTime.now().plus({ years: 3 }),
                    isDateValid: (date) => {
                        const isValidBasedOnUnavailability = this._isValidDate(date);
                        const isColor = this._isHighlightDate(date);
                        const isValidBasedOnColor = isColor !== 'red';
                        return isValidBasedOnUnavailability && isValidBasedOnColor;
                    },

                    dayCellClass: (date) => {
                        const classes = this._isCustomDate(date);
                        const is_color=this._isHighlightDate(date)
                        if (is_color == 'yellow') {
                            classes.push("special-hover-date");
                        }
                        if(is_color == 'red'){
                            classes.push("special-hover-date-red");
                        }
                        return classes.join(" ");
                    }
                },
                onApply: (start_date) => {
                    this.startDate = start_date;
                    this.endDate = start_date
                    const formattedStartDate = this.endDate.toISODate();
                    const endDateInput = this.el.querySelector('input[name="renting_end_date"]');
                    if (endDateInput) {
                        endDateInput.value = formattedStartDate;
                    }
                   
                    this._verifyValidPeriod();
                    this.$("input[name=renting_start_date]").change();
                    this.$el.trigger("daterangepicker_apply", {
                        start_date: this.startDate,
                        end_date: this.endDate,
                    });
                    console.log(this.startDate.toISODate())

                }
            },
            () => {
                const startDateInput = el.querySelector("input[name=renting_start_date]");
                return [startDateInput];
            }
        ).enable();
    },

});

WebsiteSale.include({
    events: Object.assign(WebsiteSale.prototype.events, {
        "change input[name='pricing_info_option']": '_onChangeSelectionDay',
    }),

    _get_rental_time_values($product = $){
        window.rental_time = false;
        if ($product.find("[name='pricing_info_option']:checked").length){
            window.rental_time = $product.find("[name='pricing_info_option']:checked")[0].value 
        }
        return {
            'rental_time' : window.rental_time,
            'is_from_product_page':Boolean($(".oe_website_sale input[name='product_id']").length > 0)
        }
    },

    async _onChangeSelectionDay(){
        const { rental_time, values } = await this.rpc(
            '/shop/cart/update_rental_time',
            this._get_rental_time_values()
        );
        wSaleUtils.updateCartNavBar(values);
        //$(`input[name=pricing_info_option][value='${rental_time}']`).prop('checked', true);
    },

    _updateRootProduct($form, productId) {
        this._super(...arguments);
        Object.assign(this.rootProduct, this._get_rental_time_values());
    },

});
