# -*- coding: utf-8 -*-

import base64
import datetime
import logging
from odoo import api, fields, models


class ItStockMoveReport(models.Model):
    _name = 'it.units.move.report'
    _description = "Reporte Unidades Fisicas "

    date_in = fields.Date(string='Fecha inicio')
    date_out = fields.Date(string='Fecha fin')
    business_name = fields.Many2one('res.company', string='Razon Social')
    vat = fields.Char(string='RUC')
    txt_filename = fields.Char()
    txt_binary = fields.Binary(string='Descargar Txt Sunat')

    @api.onchange("business_name")
    def _compute_it_ruc(self):
        self.vat = self.business_name.partner_id.vat or ""

    @api.multi
    def download_txt_units_sunat(self):
        content = ""
        count_sale = 0
        #stock_move_before = self.env["stock.move.line"].search([("date", "<", self.date_in_time)])


        stringventas = "%s|%s" % (
            "Hola unidades fisicas",
            "",  # campo 19
        )
        content += str(stringventas) + "\r\n"

        nametxt = 'LE%s%s%s%s%s%s%s%s.TXT' % (
            self.env.user.company_id.partner_id.vat,
            '00',
            '140100',
            '00',
            '1',
            str(count_sale),
            '1',
            '1'
        )
        self.write({
            "txt_filename": nametxt,
            "txt_binary": base64.b64encode(bytes(content, "utf-8"))
        })
        return {
            "name": "Report",
            "type": "ir.actions.act_url",
            "url": "web/content/?model=" + self._name + "&id=" + str(
                self.id) + "&filename_field=file_name&field=txt_binary&download=true&filename=" + self.txt_filename,
            "target": "new",
        }

    @api.multi
    def download_txt_valuated_sunat(self):
        content = ""
        count_sale = 0
        stringventas = "%s|%s" % (
            "Hola inventario valorizado",
            "",  # campo 19
        )
        content += str(stringventas) + "\r\n"

        nametxt = 'LE%s%s%s%s%s%s%s%s.TXT' % (
            self.env.user.company_id.partner_id.vat,
            '00',
            '140100',
            '00',
            '1',
            str(count_sale),
            '1',
            '1'
        )
        self.write({
            "txt_filename": nametxt,
            "txt_binary": base64.b64encode(bytes(content, "utf-8"))
        })
        return {
            "name": "Report",
            "type": "ir.actions.act_url",
            "url": "web/content/?model=" + self._name + "&id=" + str(
                self.id) + "&filename_field=file_name&field=txt_binary&download=true&filename=" + self.txt_filename,
            "target": "new",
        }
