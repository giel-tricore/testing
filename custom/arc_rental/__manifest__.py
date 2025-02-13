# -*- coding: utf-8 -*-
{
    'name': 'ARC Rental',
    'description': """
            ARC Rental this module for using rental product base on DateTime.
    """,
    'version': '1.0',
    'category': '',
    'summary': 'ARC Rental',
    'author': 'Spellbound Soft Solutions',
    'website': 'http://spellboundss.com/',
    'maintainer': 'Spellbound Soft Solutions',
    'company': 'Spellbound Soft Solutions',
    'depends': ['website_sale_renting', 'sale', 'sale_renting','website_sale_stock_renting','website_sale_product_configurator'],
    'data': [ 
        'data/rental_data.xml',
        'views/website_template_card_inherit.xml',
        'views/sale_order_inherit_view.xml',
        'views/sale_temporal_recurrence.xml',
        'views/rental_view.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            ('before', 'website_sale/static/src/js/website_sale.js', 'arc_rental/static/src/js/rental_inherit.js'),
            ('before', 'website_sale_product_configurator/static/src/js/sale_product_configurator_modal.js','arc_rental/static/src/js/OptionalProductsModal_Arc.js'),
            'arc_rental/static/src/css/main.css',
            'arc_rental/static/src/js/datetime_picker.js',
            'arc_rental/static/src/js/datetime_picker_popover.js',
           'arc_rental/static/src/js/datetimepicker_service.js',
            'arc_rental/static/src/js/web_rental_inherit.js',
        ]
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3'
}
