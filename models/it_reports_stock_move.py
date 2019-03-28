# -*- coding: utf-8 -*-


from odoo import api, fields, models


class ItStockMoveReport(models.Model):
    _name = 'it.units.move.report'
    _description = "Reporte Unidades Fisicas "

    date_in = fields.Date(string='Fecha inicio')
    date_out = fields.Date(string='Fecha fin')