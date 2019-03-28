# -*- coding: utf-8 -*-


from odoo import api, fields, models


class ItStockMoveReport(models.Model):
    _name = 'it.units.move.report'
    _description = "Reporte Unidades Fisicas "

    date_in = fields.Date(string='Fecha inicio')
    date_out = fields.Date(string='Fecha fin')
    business_name = fields.Many2one('res.company', string='Razon Social')
    vat = fields.Char(string='RUC')

    @api.onchange("business_name")
    def _compute_it_ruc(self):
        self.vat = self.business_name.partner_id.vat or ""