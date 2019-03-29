# -*- coding: utf-8 -*-

import base64
import datetime

from odoo import api, fields, models


class ItStockMoveReport(models.Model):
    _name = "it.units.move.report"
    _description = "Reporte Unidades Fisicas"

    date_in = fields.Date(string='Fecha inicio')
    date_out = fields.Date(string='Fecha fin')
    date_in_time = fields.Datetime(string='Fecha inicio2')
    date_out_time = fields.Datetime(string='Fecha fin2')
    business_name = fields.Many2one('res.company', string='Razon Social')
    vat = fields.Char(string='RUC')
    txt_filename = fields.Char()
    txt_binary = fields.Binary(string='Descargar Txt Sunat')
    stock_move_lines = fields.Many2many(comodel_name="stock.move.line", string="Movimientos", ondelete="cascade")

    # tipo operacion = ["A","M","C"] => M),
    #     }

    @api.onchange("business_name")
    def _compute_it_ruc(self):
        self.vat = self.business_name.partner_id.vat or ""

    @api.one
    def generate_moves(self):
        d_ref = datetime.datetime.strptime(self.date_out, "%Y-%m-%d")
        d_ref_out = datetime.datetime.strptime(self.date_out, "%Y-%m-%d")
        d_ref_in = datetime.datetime.strptime(self.date_in, "%Y-%m-%d")
        # d_ref = [datetime.datetime.fromtimestamp(self.date_out, "%Y-%m-%d")]
        month = "%02d" % (d_ref.month,)
        # DECLARAR FECHAS

        date_in_before = datetime.datetime.combine(datetime.date(d_ref_in.year, d_ref_in.month, d_ref_in.day),
                                                   datetime.time(0, 0, 0))
        date_out_after = datetime.datetime.combine(datetime.date(d_ref_out.year, d_ref_out.month, d_ref_out.day),
                                                   datetime.time(23, 59, 59))
        self.date_in_time = date_in_before
        self.date_out_time = date_out_after

        stock_move_after = self.env["stock.move.line"].search(
            [("date", ">=", self.date_in_time), ("date", "<=", self.date_out_time)])
        arry_stock = []
        if stock_move_after:
            for before_in in stock_move_after:
                a = before_in.location_id.usage
                b = before_in.location_dest_id.usage
                if (a == 'internal') and (b != 'internal'):
                    arry_stock.append(before_in)
                if (a == 'internal') and (b == 'internal'):
                    # PENDIENTE MOVIMIENTO ENTRE ALMACENES QUE VAN AL ESTE REPORTE
                    pass
                if (a != 'internal') and (b == 'internal'):
                    arry_stock.append(before_in)
            self.stock_move_lines = arry_stock

    @api.multi
    def download_txt_units_sunat(self):
        content = ""
        count_sale = 0
        d_ref = datetime.datetime.strptime(self.date_out, "%Y-%m-%d")
        d_ref_out = datetime.datetime.strptime(self.date_out, "%Y-%m-%d")
        d_ref_in = datetime.datetime.strptime(self.date_in, "%Y-%m-%d")
        # d_ref = [datetime.datetime.fromtimestamp(self.date_out, "%Y-%m-%d")]
        month = "%02d" % (d_ref.month,)
        # DECLARAR FECHAS

        date_in_before = datetime.datetime.combine(datetime.date(d_ref_in.year, d_ref_in.month, d_ref_in.day),
                                                   datetime.time(0, 0, 0))
        date_out_after = datetime.datetime.combine(datetime.date(d_ref_out.year, d_ref_out.month, d_ref_out.day),
                                                   datetime.time(23, 59, 59))
        self.date_in_time = date_in_before
        self.date_out_time = date_out_after

        stock_move_after = self.env["stock.move.line"].search(
            [("date", ">=", self.date_in_time), ("date", "<=", self.date_out_time)])

        for stock_out in stock_move_after:
            stringventas = "%s|%s|%s" % (
                str(d_ref.year) + "" + str(month) + "00",  # campo 1
                str("M") + str(stock_out.id),  # campo 2
                stock_out.qty_done or 0,  # campo 3
            )
            content += str(stringventas) + "\r\n"

        nametxt = 'LE%s%s%s%s%s%s%s%s%s%s.TXT' % (
            self.env.user.company_id.partner_id.vat,
            d_ref.year,  # Year
            month,  # Month
            '00',
            '120100',
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
            '130100',
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
