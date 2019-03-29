# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockMoveLineInherit(models.Model):
    _inherit = 'stock.move.line'
    _description = "Kardex de unidades fisicas"

    stock_inicial = fields.Char()
