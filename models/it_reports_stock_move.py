# -*- coding: utf-8 -*-

import base64
import datetime
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


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
    # stock_move_lines = fields.Many2many(comodel_name="stock.move.line", string="Movimientos", ondelete="cascade")
    stock_phisical_lines = fields.One2many('it.units.move.report.phisical.line', 'report_id',
                                           string="Movimientos",
                                           ondelete="cascade")
    stock_valuated_lines = fields.One2many('it.units.move.report.phisical.line', 'report_id',
                                           string="Movimientos",
                                           ondelete="cascade")

    # tipo operacion = ["A","M","C"] => M),
    #     }

    @api.multi
    def unlink(self):
        if self.stock_phisical_lines:
            self.stock_phisical_lines.unlink()
        if self.stock_valuated_lines:
            self.stock_valuated_lines.unlink()
        res = super(ItStockMoveReport, self).unlink()
        return res

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

        # GENERAR UN LOOP PARA OBTENER LOS SALDOS INCIALES:
        # {} INGRESAR LOGICA PARA OBTENER EL SALDO INICIAL
        # REGISTRAR SOBRE EL NUEVO MODELO
        # TIPO 1 PARA SALDO INICIAL
        # --------------------------------------------------
        context = {'to_date': self.date_in_time}
        initial = self.env["product.product"].with_context(context).search(
            [('type', '=', 'product'), ('qty_available', '!=', 0)])
        for product in initial:
            json_stock_phisical = {
                "type": 1,
                "date": self.date_in_time,
                "reference": "SALDO INICIAL",
                "in_entrada": product.qty_at_date,
                "report_id": self.id,
                "product_id": product.id,
                "in_saldo": product.stock_value
            }
            res_phisical = self.env["it.units.move.report.phisical.line"].sudo().create(json_stock_phisical)
        # ========================================================

        entry_balance = self.env["account.move.line"].search(
            [("date", ">=", self.date_in_time), ("date", "<=", self.date_out_time), ('user_type_id', '=', 5)])
        if entry_balance:
            for valor in entry_balance:

                json_stock_phisical = {
                    "date": valor.date,
                    "in_saldo": valor.debit,
                    "out_saldo": valor.credit,
                    "reference": "Ajuste de Costos",
                    "report_id": self.id,
                    "product_id": valor.product_id.id

                }
                res_phisical = self.env["it.units.move.report.phisical.line"].sudo().create(json_stock_phisical)

        # ========================================================

        stock_move_after = self.env["stock.move"].search(
            [("date", ">=", self.date_in_time), ("date", "<=", self.date_out_time)])

        if stock_move_after:
            for before_in in stock_move_after:
                a = before_in.location_id.usage
                b = before_in.location_dest_id.usage
                if (a == 'internal') and (b != 'internal'):
                    json_stock_phisical = {
                        "type": 0,
                        "date": before_in.date,
                        "reference": before_in.reference,
                        "report_id": self.id,
                        "out_salida": before_in.product_uom_qty,
                        "product_id": before_in.product_id.id,
                        "out_saldo": before_in.price_unit * (- before_in.product_uom_qty),
                        # otros campos para el txt
                        "existence": before_in.product_id.it_existence.code

                        #

                    }
                    res_phisical = self.env["it.units.move.report.phisical.line"].sudo().create(json_stock_phisical)

                if (a == 'internal') and (b == 'internal'):
                    # PENDIENTE MOVIMIENTO ENTRE ALMACENES QUE VAN AL ESTE REPORTE
                    pass
                if (a != 'internal') and (b == 'internal'):
                    json_stock_phisical = {
                        "type": 0,
                        "date": before_in.date,
                        "reference": before_in.reference,
                        "report_id": self.id,
                        "in_entrada": before_in.product_uom_qty,
                        "product_id": before_in.product_id.id,
                        "in_saldo": before_in.price_unit * before_in.product_uom_qty,

                        # "in_saldo": before_in.stock_move_id.amount
                        "existence": before_in.product_id.it_existence.code
                    }
                    res_phisical = self.env["it.units.move.report.phisical.line"].sudo().create(json_stock_phisical)

    @api.multi
    def download_txt_units_sunat(self):
        content = ""
        count_sale = 0
        d_ref = datetime.datetime.strptime(self.date_out, "%Y-%m-%d")
        d_ref_out = datetime.datetime.strptime(self.date_out, "%Y-%m-%d")
        d_ref_in = datetime.datetime.strptime(self.date_in, "%Y-%m-%d")
        # d_ref = [datetime.datetime.fromtimestamp(self.date_out, "%Y-%m-%d")]
        month = "%02d" % (d_ref.month,)
        date_in_before = datetime.datetime.combine(datetime.date(d_ref_in.year, d_ref_in.month, d_ref_in.day),
                                                   datetime.time(0, 0, 0))
        date_out_after = datetime.datetime.combine(datetime.date(d_ref_out.year, d_ref_out.month, d_ref_out.day),
                                                   datetime.time(23, 59, 59))
        self.date_in_time = date_in_before
        self.date_out_time = date_out_after

        stock_move_lines = self.env["it.units.move.report.phisical.line"].search(
            [("date", ">=", self.date_in_time), ("date", "<=", self.date_out_time)])

        for stock_out in stock_move_lines:
            stringventas = "%s|%s|%s" % (
                str(d_ref.year) + "" + str(month) + "00",  # campo 1
                str("M") + str(stock_out.id),  # campo 2
                stock_out.existence or 0,  # campo 3
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


class ItStockMoveReportPhisicalLine(models.Model):
    _name = "it.units.move.report.phisical.line"
    _description = "Reporte Unidades Fisicas Detalle"

    type = fields.Integer(string="Es Saldo inicial?", help="1. Es saldo inicial, 0. No es saldo incial")
    date = fields.Datetime(string="Fecha")
    reference = fields.Char(string="Referencia")
    report_id = fields.Many2one("it.units.move.report", "Reporte")
    product_id = fields.Many2one("product.product", "Producto")
    in_entrada = fields.Float(string="Entrada")
    out_salida = fields.Float(string="Salida")
    # qty_done = fields.Float(string="Cantidad")

    # type_move = fields.Selection([("in", "Entrada"), ("out", "Salida")],
    #                            string="Tipo de movimiento", ondelete="cascade")

    # CAMPOS ADICIONALES PARA EL REPORTE DE INVENTARIO VALORIZADO

    in_saldo = fields.Float(string="Saldo Entrada")
    out_saldo = fields.Float(string="Saldo Salida")
    name_val = fields.Float(string="valor")
    existence = fields.Char(string="existence")
