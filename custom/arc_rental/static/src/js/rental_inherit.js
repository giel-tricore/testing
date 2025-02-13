/** @odoo-module **/

import VariantMixin from "@website_sale/js/sale_variant_mixin";
import { OptionalProductsModal } from "@website_sale_product_configurator/js/sale_product_configurator_modal";


if ($("input[name='renting_start_date']").is(":visible")) {
    setTimeout(() => $("input[name='renting_start_date']").change(), 1000);
}

const RentalTimeMixin = {
    _get_rental_time_values($product) {
        if (!$product || !$product.length) {
            console.warn("RentalTimeMixin: $product is undefined or empty.");
            return { rental_time: false };
        }

        let rental_time = false;
        const checkedOption = $product.find("[name='pricing_info_option']:checked");
        if (checkedOption.length) {
            rental_time = checkedOption.val();
        }
        return { rental_time };
    },

    _onChangeTimeCombination($ev, $parent, combination) {
        if (combination.all_slots) {
            combination.all_slots.forEach((item) => {
                const $slot = $("#" + item);
                const statusContainer = $slot.closest("td").find(".availability-status");
                $slot.prop("disabled", false);
                statusContainer.find(".text-success").removeClass("d-none");
                statusContainer.find(".text-danger").addClass("d-none");
            });

            combination.booked_slot.forEach((item) => {
                const $slot = $("#" + item);
                const statusContainer = $slot.closest("td").find(".availability-status");
                $slot.prop("disabled", true);
                statusContainer.find(".text-success").addClass("d-none");
                statusContainer.find(".text-danger").removeClass("d-none");
            });

            const value = $('input[name="pricing_info_option"]:checked').val();
            $(".js_check_product").toggleClass(
                "d-none",
                combination.booked_slot.length === combination.all_slots.length || !value
            );
        }
    }
};


const oldGetOptionalCombinationInfoParam = VariantMixin._getOptionalCombinationInfoParam;
VariantMixin._get_rental_time_values = RentalTimeMixin._get_rental_time_values;
VariantMixin._getOptionalCombinationInfoParam = function ($product) {
	const result = oldGetOptionalCombinationInfoParam.apply(this, arguments);
    if (!this.isWebsite) {
		return result;
    }
    Object.assign(result, this._get_rental_time_values($product));
    return result;
};

VariantMixin._onChangeCombination = (function (originalFunction) {
    return function ($ev, $parent, combination) {
        if (originalFunction) {
            originalFunction.apply(this, arguments);
        }
        RentalTimeMixin._onChangeTimeCombination.call(this, $ev, $parent, combination);
    };
})(VariantMixin._onChangeCombination);

OptionalProductsModal.include({
    _onChangeCombination(ev, $parent, combination) {
        if (combination.is_rental) {
            combination.price = combination.current_rental_price;
        }
        this._super.apply(this, arguments);
        RentalTimeMixin._onChangeTimeCombination.call(this, ev, $parent, combination);
    },
});
