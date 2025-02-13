/** @odoo-module **/

import { OptionalProductsModal } from "@website_sale_product_configurator/js/sale_product_configurator_modal";

OptionalProductsModal.include({

     _computePriceTotal: function () {
        if (this.$modal.find('.js_price_total').length) {
            var price = 0;
            this.$modal.find('.js_product.in_cart').each(function () {
                var quantity = parseFloat($(this).find('input[name="add_qty"]').first().val().replace(',', '.') || 1);
                var $selectedOption = $("input[name='pricing_info_option']:checked");
                if ($selectedOption.length) {
                    // Get the corresponding row
                    var $row = $selectedOption.closest("tr");
                    var slot_price = $row.find(".oe_currency_value").text().trim();
                    var duration = $selectedOption.data("duration");
                    if(duration){
                        $(this).find(".o_renting_duration").text(duration);
                    }
                    $(this).find(".js_raw_price").text(slot_price);
                    $(this).find(".oe_price .oe_currency_value").text(slot_price);

                }
                //$(this).find('.js_raw_price').html('45')
                //$(this).find('.oe_price .oe_currency_value').html('45')
                price += parseFloat($(this).find('.js_raw_price').html()) * quantity;
            });

            this.$modal.find('.js_price_total .oe_currency_value').text(
                this._priceToStr(parseFloat(price))
            );
        }
    },
});
