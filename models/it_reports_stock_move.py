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
    stock_valuated_lines = fields.One2many('it.units.move.report.valuated.line', 'report_id',
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
                "is_saldo": "AAAA",
                "in_entrada": product.qty_at_date,
                "report_id": self.id,
                "product_id": product.id,
                # campos adicionales
                "stock_id": product.id,
                "type_operation": "16",
                "product_name": product.name,
                "existence": product.it_existence.code,
                "units_med": product.uom_id.code_unit_measure.code
            }
            res_phisical = self.env["it.units.move.report.phisical.line"].sudo().create(json_stock_phisical)
        # ========================================================

        stock_move_after = self.env["stock.move"].search(
            [("date", ">=", self.date_in_time), ("date", "<=", self.date_out_time)])

        if stock_move_after:
            for before_in in stock_move_after:
                a = before_in.location_id.usage
                b = before_in.location_dest_id.usage
                if before_in.create_uid == 6:
                    self.type_operation = "6"
                    if before_in.create_uid == 10:
                        self.type_operation = "10"
                        if before_in.create_uid == 12:
                            self.type_operation = "12"
                if (a == 'internal') and (b != 'internal'):
                    json_stock_phisical = {
                        "type": 0,
                        "date": before_in.date,
                        "reference": before_in.reference,
                        "report_id": self.id,
                        "out_salida": before_in.product_uom_qty,
                        "product_id": before_in.product_id.id,
                        # OTROS CAMPOS  PARA EL TXTSUNAT
                        "stock_id": before_in.id,
                        "existence": before_in.product_id.it_existence.code,
                        "existence_id": before_in.product_id.it_existence.id,
                        "date_gr": before_in.picking_id.it_date_gr,
                        "catalog_01_id": before_in.picking_id.catalog_01_id.code,
                        "series": before_in.picking_id.series.series,
                        "correlative": before_in.picking_id.correlative,
                        "type_operation": before_in.picking_id.type_transaction.code,
                        "product_name": before_in.product_id.name,
                        "units_med": before_in.product_id.uom_id.code_unit_measure.code

                        #

                    }
                    res_phisical = self.env["it.units.move.report.phisical.line"].sudo().create(json_stock_phisical)

                if (a == 'internal') and (b == 'internal'):
                    if before_in.picking_type_id.it_is_kardex is True:
                        json_stock_phisical = {
                            "type": 0,
                            "date": before_in.date,
                            "reference": before_in.reference,
                            "report_id": self.id,
                            "in_entrada": before_in.product_uom_qty,
                            "product_id": before_in.product_id.id,
                            "stock_id": before_in.id,
                        }
                        res_phisical = self.env["it.units.move.report.phisical.line"].sudo().create(json_stock_phisical)
                    # PENDIENTE MOVIMIENTO ENTRE ALMACENES QUE VAN AL ESTE REPORTE

                if (a != 'internal') and (b == 'internal'):
                    json_stock_phisical = {
                        "type": 0,
                        "date": before_in.date,
                        "reference": before_in.reference,
                        "report_id": self.id,
                        "in_entrada": before_in.product_uom_qty,
                        "product_id": before_in.product_id.id,
                        # OTROS CAMPOS  PARA EL TXTSUNAT
                        "stock_id": before_in.id,
                        "existence": before_in.product_id.it_existence.code,
                        "existence_id": before_in.product_id.it_existence.id,
                        "date_gr": before_in.picking_id.it_date_gr,
                        "catalog_01_id": before_in.picking_id.catalog_01_id.code,
                        "series": before_in.picking_id.series.series,
                        "correlative": before_in.picking_id.correlative,
                        "type_operation": before_in.picking_id.type_transaction.code,
                        "product_name": before_in.product_id.name,
                        "units_med": before_in.product_id.uom_id.code_unit_measure.code

                    }
                    res_phisical = self.env["it.units.move.report.phisical.line"].sudo().create(json_stock_phisical)
        #  ====================================================================================================
        #  REPORTE DE INVENTARIO VALORIZADO
        #  ====================================================================================================
        context = {'to_date': self.date_in_time}
        initial = self.env["product.product"].with_context(context).search(
            [('type', '=', 'product'), ('qty_available', '!=', 0)])
        for product in initial:
            json_stock_phisical = {
                "type": 1,
                "date": self.date_in_time,
                "reference": "SALDO INICIAL",
                "is_saldo": "AAAA",
                "in_entrada": product.qty_at_date,
                "report_id": self.id,
                "product_id": product.id,
                "in_saldo": product.stock_value,
                # campos adicionales
                "stock_id": product.id,
                "type_operation": "16",
                "product_name": product.name,
                "existence": product.it_existence.code,
                "units_med": product.uom_id.code_unit_measure.code
            }
            res_phisical = self.env["it.units.move.report.valuated.line"].sudo().create(json_stock_phisical)
        # ========================================================

        entry_balance = self.env["account.move.line"].search(
            [("date", ">=", self.date_in_time), ("date", "<=", self.date_out_time), ('user_type_id', '=', 5)])
        if entry_balance:
            for valor in entry_balance:
                json_stock_phisical = {
                    "date": valor.create_date,
                    "in_saldo": valor.debit,
                    "out_saldo": valor.credit,
                    "reference": "Ajuste de Costos",
                    "report_id": self.id,
                    "product_id": valor.product_id.id,
                    # campos adicionales
                    "product_name": valor.product_id.name,

                }
                res_phisical = self.env["it.units.move.report.valuated.line"].sudo().create(json_stock_phisical)

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
                        # OTROS CAMPOS  PARA EL TXTSUNAT
                        "stock_id": before_in.id,
                        "existence": before_in.product_id.it_existence.code,
                        "existence_id": before_in.product_id.it_existence.id,
                        "date_gr": before_in.picking_id.it_date_gr,
                        "catalog_01_id": before_in.picking_id.catalog_01_id.code,
                        "series": before_in.picking_id.series.series,
                        "correlative": before_in.picking_id.correlative,
                        "type_operation": before_in.picking_id.type_transaction.code,
                        "product_name": before_in.product_id.name,
                        "units_med": before_in.product_id.uom_id.code_unit_measure.code

                    }
                    res_phisical = self.env["it.units.move.report.valuated.line"].sudo().create(json_stock_phisical)

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
                        # OTROS CAMPOS  PARA EL TXTSUNAT
                        "stock_id": before_in.id,
                        "existence": before_in.product_id.it_existence.code,
                        "existence_id": before_in.product_id.it_existence.id,
                        "date_gr": before_in.picking_id.it_date_gr,
                        "catalog_01_id": before_in.picking_id.catalog_01_id.code,
                        "series": before_in.picking_id.series.series,
                        "correlative": before_in.picking_id.correlative,
                        "type_operation": before_in.picking_id.type_transaction.code,
                        "product_name": before_in.product_id.name,
                        "units_med": before_in.product_id.uom_id.code_unit_measure.code
                    }
                    res_phisical = self.env["it.units.move.report.valuated.line"].sudo().create(json_stock_phisical)

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

        for stock_out in self.stock_phisical_lines:
            stringunits = "%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s" % (
                str(d_ref.year) + "" + str(month) + "00",  # campo 1
                str("M") + str(stock_out.stock_id),  # campo 2
                "",  # campo 3
                "",  # campo 4
                "",  # campo 5
                stock_out.existence or "",  # campo 6
                stock_out.existence_id or "",  # campo 7
                "",  # campo 8
                stock_out.date_gr or "",  # campo 9
                stock_out.catalog_01_id or "",  # campo 10
                stock_out.series or "",  # campo 11
                stock_out.correlative or "",  # campo 12
                stock_out.type_operation or "",  # campo 13 tipo operacion efect
                stock_out.product_name or "",  # campo 14   descripcion de la exist
                stock_out.units_med or "",  # campo 15  cod uni med
                stock_out.in_entrada or 0,  # campo 16 entrada
                stock_out.in_saldo or 0,  # campo 17  salida
                stock_out.out_salida or 0,  # campo 18  salida
                stock_out.out_saldo or 0,  # campo 19  salida
                "",  # campo 20
                "",  # campo 21

            )
            content += str(stringunits) + "\r\n"
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

        for stock_out in self.stock_valuated_lines:
            stringvaluated = "%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s" % (
                str(d_ref.year) + "" + str(month) + "00",  # campo 1
                str("M") + str(stock_out.stock_id),  # campo 2
                "",  # campo 3
                "",  # campo 4
                "",  # campo 5
                stock_out.existence or "",  # campo 6
                stock_out.existence_id or "",  # campo 7
                "",  # campo 8
                stock_out.date_gr or "",  # campo 9
                stock_out.catalog_01_id or "",  # campo 10
                stock_out.series or "",  # campo 11
                stock_out.correlative or "",  # campo 12
                stock_out.type_operation or "",  # campo 13 tipo operacion efect
                stock_out.product_name or "",  # campo 14   descripcion de la exist
                stock_out.units_med or "",  # campo 15  cod uni med
                stock_out.in_entrada or 0,  # campo 16
                stock_out.out_salida or 0,  # campo 17
                "",  # campo 17
                "",  # campo 17

            )
            content += str(stringvaluated) + "\r\n"

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
    _order = "product_name, is_saldo, date asc"

    type = fields.Integer(string="Es Saldo inicial?", help="1. Es saldo inicial, 0. No es saldo incial")
    date = fields.Datetime(string="Fecha")
    reference = fields.Char(string="Referencia")
    report_id = fields.Many2one("it.units.move.report", "Reporte")
    product_id = fields.Many2one("product.product", "Producto")
    in_entrada = fields.Float(string="Entrada")
    out_salida = fields.Float(string="Salida")
    # qty_done = fields.Float(string="Cantidad")
    is_saldo = fields.Char(string="saldo inicial")

    # CAMPOS ADICIONALES PARA EL REPORTE DE INVENTARIO VALORIZADO
    stock_id = fields.Char()
    existence = fields.Char()
    existence_id = fields.Char()
    date_gr = fields.Char()
    catalog_01_id = fields.Char()
    series = fields.Char()
    correlative = fields.Char()
    type_operation = fields.Char()
    product_name = fields.Char()
    units_med = fields.Char()


class ItStockMoveReportValuatedLine(models.Model):
    _name = "it.units.move.report.valuated.line"
    _description = "Reporte Inventario Valorizado Detalle"
    _order = "product_name, is_saldo, date asc"

    type = fields.Integer(string="Es Saldo inicial?", help="1. Es saldo inicial, 0. No es saldo incial")
    date = fields.Datetime(string="Fecha")
    reference = fields.Char(string="Referencia")
    report_id = fields.Many2one("it.units.move.report", "Reporte")
    product_id = fields.Many2one("product.product", "Producto")
    in_entrada = fields.Float(string="Entrada")
    out_salida = fields.Float(string="Salida")
    # qty_done = fields.Float(string="Cantidad")
    is_saldo = fields.Char(string="saldo inicial")

    # CAMPOS ADICIONALES PARA EL REPORTE DE INVENTARIO VALORIZADO
    in_saldo = fields.Float(string="Saldo Entrada", digits=(12, 2), default=0.00, )
    out_saldo = fields.Float(string="Saldo Salida", digits=(12, 2), default=0.00, )
    name_val = fields.Float(string="valor")
    existence = fields.Char(string="existence")
    # ====================================================
    stock_id = fields.Char()
    existence_id = fields.Char()
    date_gr = fields.Char()
    catalog_01_id = fields.Char()
    series = fields.Char()
    correlative = fields.Char()
    type_operation = fields.Char()
    product_name = fields.Char()
    units_med = fields.Char()
