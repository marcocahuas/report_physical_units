# -*- coding: utf-8 -*-
###############################################################################
# UNIDADES FISICAS y INVENTARIO VALORIZADO
###############################################################################
{
    "name": "Reports Stock Move",
    "version": "0.1",
    "category": "Custom developer",
    "author": "Inti Tec Peru",
    "sequence": 1,
    "website": "https://www.intitecperu.com/",
    "contributors": [
        "Kelvin Meza <kelvin.meza@intitecperu.com>",
    ],
    "summary": "Physical units - valued inventory",
    "description": "",
    "depends": ["base", 'stock'],
    "data": [
        'views/it_reports_stock_move.xml',
        #'views/it_stock_move_line_inherit.xml',
    ],
    'images': [
        'static/description/intitecperu.png',
    ],
    "installable": True,
    "application": True,
}
