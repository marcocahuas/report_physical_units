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
    "depends": ["base", 'stock', 'intitec_localizacion_PE_v11'],
    "data": [
        'views/it_reports_stock_move.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
    ],
    'images': [
        'static/description/intitecperu.png',
    ],
    "installable": True,
    "application": True,
}
