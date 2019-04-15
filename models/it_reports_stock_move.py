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
                                           string="Kardex",
                                           ondelete="cascade")
    stock_valuated_lines = fields.One2many('it.units.move.report.valuated.line', 'report_id',
                                           string="Kardex",
                                           ondelete="cascade")

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
        if self.stock_phisical_lines:
            self.stock_phisical_lines.unlink()

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
        # --------------------------------------------------
        #
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
                "establecimiento": "0001",
                "catalogo_existence": "9",
                "existence_id": "OTROS",
                "codigo_propio": "6000000000000000",
                "type_operation": "16",
                "product_name": product.name,
                "date_gr": self.date_in_time,
                "catalog_01_id": "00",
                "series": "0",
                "correlative": "0",
                "existence": product.it_existence.code,
                "units_med": product.uom_id.code_unit_measure.code
                # "saldo_entrada": 0.0,
                # "saldo_salida": 0.0
            }
            res_phisical = self.env["it.units.move.report.phisical.line"].sudo().create(json_stock_phisical)
        # ---------------------------------------------------

        # OBTENEMOS LOS MOVIMIENTOS
        stock_move_after = self.env["stock.move"].search(
            [("date", ">=", self.date_in_time), ("date", "<=", self.date_out_time), ("state", "=", "done")])

        if stock_move_after:
            for before_in in stock_move_after:
                # OBTENEMOS LA REFERENCIA PARA EL CAMPO TIPO DOC
                stock_account_after = self.env["account.invoice"].search(
                    [("origin", "=", before_in.picking_id.origin or "-")], limit=1)
                if stock_account_after is not False:
                    fecha = stock_account_after.date_invoice
                    tipo_doc = stock_account_after.catalog_01_id.code
                    serie = stock_account_after.series.series
                    correlativo = stock_account_after.correlative

                a = before_in.location_id.usage
                b = before_in.location_dest_id.usage
                it_code = before_in.location_id.it_establishment.code
                it_des_code = before_in.location_dest_id.it_establishment.code
                type_operation_sunat = ""
                is_scrap = before_in.location_dest_id.scrap_location

                # PRODUCCION A UNA INTERNAL TP = 19 =>ENTRADA
                if (a == "production") and (b == "internal"):
                    type_operation_sunat = "19"  # Cambiar
                    fecha = before_in.date
                    tipo_doc = "00"
                    serie = "0"
                    correlativo = "0"
                # INTERNAL A UNA PRODUCCION TP = 10 =>SALIDA
                if (a == "internal") and (b == "production"):
                    type_operation_sunat = "10"
                    fecha = before_in.date
                    tipo_doc = "00"
                    serie = "0"
                    correlativo = "0"
                # INTERNAL A UN CLIENTE TP = 01 =>SALIDA
                if (a == "internal") and (b == "customer"):
                    type_operation_sunat = "01"
                # CUSTOMER A INTERNAL ENTRADA X DEVOLUCION TP=24 => ENTRADA
                if (a == "customer") and (b == "internal"):
                    type_operation_sunat = "24"
                # INVENTORY A INTERNAL VS AJUSTES = 28 =>SALIDA
                if (a == "inventory") and (b == "internal"):
                    type_operation_sunat = "28"
                # INVENTORY A INTERNAL AJUSTES = 28 =>ENTRADA
                if (a == "internal") and (b == "inventory"):
                    type_operation_sunat = "28"
                #  INTERNAL INVENTORY IF MERMAS
                if (a == "internal") and (b == "inventory"):
                    if is_scrap is True:
                        type_operation_sunat = "13"
                #  INTERNAL INVENTORY SALIDA X DEVOLUCION TP= 25 => SALIDA
                if (a == "internal") and (b == "supplier"):
                    type_operation_sunat = "25"
                # INTERNAL A PRODUCTION DESECHOS TP=99 => SALIDA
                # if (a == "internal") and (b == "production"):
                #     if before_in.location_id.is_kardex is True:
                #         type_operation_sunat = "99"  # falta analizar

                if before_in.picking_id.type_transaction.code is not False:
                    type_operation_sunat = before_in.picking_id.type_transaction.code
                # DECLARAMOS LOS CAMPOS DEL TIPO DE DOCUMENTOS PARA MOSTRAR
                if fecha is False:
                    fecha = before_in.picking_id.it_date_gr
                    if before_in.picking_id.it_date_gr is False:
                        fecha = before_in.picking_id.scheduled_date

                if before_in.picking_id.catalog_01_id.code is not False:
                    tipo_doc = before_in.picking_id.catalog_01_id.code

                if serie is False:
                    serie = before_in.picking_id.series.series
                    if before_in.picking_id.series.series is False:
                        serie = before_in.picking_id.serie

                if correlativo is False:
                    correlativo = before_in.picking_id.correlative
                    if before_in.picking_id.correlative is False:
                        correlativo = before_in.picking_id.it_correlative_manual

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
                        "establecimiento": before_in.location_id.it_establishment.code,
                        "catalogo_existence": "9",
                        "codigo_propio": "6000000000000000",
                        "existence": before_in.product_id.it_existence.code,
                        "existence_id": "OTROS",
                        "date_gr": fecha,
                        "catalog_01_id": tipo_doc,
                        "series": serie,
                        "correlative": correlativo,
                        "type_operation": type_operation_sunat,
                        "product_name": before_in.product_id.name,
                        "units_med": before_in.product_id.uom_id.code_unit_measure.code,
                        # saldo final
                        # identificar el saldo inicial
                    }
                    res_phisical = self.env["it.units.move.report.phisical.line"].sudo().create(json_stock_phisical)

                if (a == 'internal') and (b == 'internal') \
                        and (before_in.picking_type_id.it_is_kardex is True):
                    if (it_code is not False) and (it_des_code is False):
                        if before_in.location_id.is_kardex is False and before_in.location_dest_id.is_kardex is not True:
                            json_stock_phisical = {
                                "type": 0,
                                "date": before_in.date,
                                "reference": before_in.reference,
                                "report_id": self.id,
                                "out_salida": before_in.product_uom_qty,
                                "product_id": before_in.product_id.id,
                                # OTROS CAMPOS  PARA EL TXTSUNAT
                                "stock_id": before_in.id,
                                "establecimiento": before_in.location_id.it_establishment.code,
                                "catalogo_existence": "9",
                                "codigo_propio": "6000000000000000",
                                "existence": before_in.product_id.it_existence.code,
                                "existence_id": "OTROS",
                                "date_gr": fecha,
                                "catalog_01_id": tipo_doc,
                                "series": serie,
                                "correlative": correlativo,
                                "type_operation": type_operation_sunat,
                                "product_name": before_in.product_id.name,
                                "units_med": before_in.product_id.uom_id.code_unit_measure.code
                            }
                            res_phisical = self.env["it.units.move.report.phisical.line"].sudo().create(
                                json_stock_phisical)

                if (a == 'internal') and (b == 'internal') \
                        and (before_in.picking_type_id.it_is_kardex is True):
                    if (it_des_code is not False) and (it_code is False):
                        if before_in.location_dest_id.is_kardex is False and before_in.location_id.is_kardex is not True:
                            json_stock_phisical = {
                                "type": 0,
                                "date": before_in.date,
                                "reference": before_in.reference,
                                "report_id": self.id,
                                "in_entrada": before_in.product_uom_qty,
                                "product_id": before_in.product_id.id,
                                # OTROS CAMPOS  PARA EL TXTSUNAT
                                "stock_id": before_in.id,
                                "establecimiento": before_in.location_dest_id.it_establishment.code,
                                "catalogo_existence": "9",
                                "codigo_propio": "6000000000000000",
                                "existence": before_in.product_id.it_existence.code,
                                "existence_id": "OTROS",
                                "date_gr": fecha,
                                "catalog_01_id": tipo_doc,
                                "series": serie,
                                "correlative": correlativo,
                                "type_operation": type_operation_sunat,
                                "product_name": before_in.product_id.name,
                                "units_med": before_in.product_id.uom_id.code_unit_measure.code
                            }
                            res_phisical = self.env["it.units.move.report.phisical.line"].sudo().create(
                                json_stock_phisical)

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
                        "establecimiento": before_in.location_dest_id.it_establishment.code,
                        "catalogo_existence": "9",
                        "codigo_propio": "6000000000000000",
                        "existence": before_in.product_id.it_existence.code,
                        "existence_id": "OTROS",
                        "date_gr": fecha,
                        "catalog_01_id": tipo_doc,
                        "series": serie,
                        "correlative": correlativo,
                        "type_operation": type_operation_sunat,
                        "product_name": before_in.product_id.name,
                        "units_med": before_in.product_id.uom_id.code_unit_measure.code
                    }
                    res_phisical = self.env["it.units.move.report.phisical.line"].sudo().create(json_stock_phisical)

        #  ====================================================================================================
        #  REPORTE DE INVENTARIO VALORIZADO
        #  ====================================================================================================
        # OBTENEMOS EL SALDO INICIAL
        context = {'to_date': self.date_in_time}
        initial = self.env["product.product"].with_context(context).search(
            [('type', '=', 'product'), ('qty_available', '!=', 0)])
        for product in initial:
            json_stock_phisical = {
                "type": 1,
                "date": self.date_in_time,
                "reference": "aa SALDO INICIAL",
                "is_saldo": "AAAA",
                "in_entrada": product.qty_at_date,
                "report_id": self.id,
                "product_id": product.id,
                # campos adicionales
                "stock_id": product.id,
                "establecimiento": "0001",
                "catalogo_existence": "9",
                "existence_id": "OTROS",
                "codigo_propio": "6000000000000000",
                "type_operation": "16",
                "product_name": product.name,
                "date_gr": self.date_in_time,
                "catalog_01_id": "00",
                "series": "0",
                "correlative": "0",
                "existence": product.it_existence.code,
                "units_med": product.uom_id.code_unit_measure.code,

                "in_saldo": product.stock_value,  # Entradas Costo Unit.
                "calculo_unit_in": (product.stock_value / product.qty_at_date),
                "cantidad_saldo_final": product.qty_at_date,
                "costo_unit_final": (product.stock_value / product.qty_at_date),
                "costo_total_final": product.stock_value

            }
            res_phisical = self.env["it.units.move.report.valuated.line"].sudo().create(json_stock_phisical)
        # ========================================================
        # TRAEMOS AJUSTE DE COSTOS

        entry_balance = self.env["account.move.line"].search(
            [("date", ">=", self.date_in_time), ("date", "<=", self.date_out_time), ('user_type_id', '=', 5)])
        for valor in entry_balance:
            json_stock_phisical = {
                "date": valor.create_date,
                "in_saldo": valor.debit,
                "out_saldo": valor.credit,
                "reference": "AJUSTE DE COSTOS",
                "report_id": self.id,
                "product_id": valor.product_id.id,
                "calculo_unit_out": "0.00",
                # campos adicionales
                "establecimiento": "0001",
                "existence": "9",
                "existence_id": "OTROS",
                "codigo_propio": "6000000000000000",
                "product_name": valor.product_id.name,
                "date_gr": self.date_in_time,
                "catalog_01_id": "00",
                "series": "0",
                "correlative": "0",
                "type_operation": "99",
                "stock_id": valor.id,
                "units_med": "NIU"  # valor.product_id.uom_id.code_unit_measure.code  # ver si tiene unidad de medida

            }
            res_phisical = self.env["it.units.move.report.valuated.line"].sudo().create(json_stock_phisical)

        # OBTENEMOS LOS MOVIMIENTOS
        stock_move_after = self.env["stock.move"].search(
            [("date", ">=", self.date_in_time), ("date", "<=", self.date_out_time), ("state", "=", "done")])

        if stock_move_after:
            for before_in in stock_move_after:
                # OBTENEMOS LA REFERENCIA PARA EL CAMPO TIPO DOC

                stock_account_after = self.env["account.invoice"].search(
                    [("origin", "=", before_in.picking_id.origin or "-")], limit=1)
                if stock_account_after is not False:
                    fecha = stock_account_after.date_invoice
                    tipo_doc = stock_account_after.catalog_01_id.code
                    serie = stock_account_after.series.series
                    correlativo = stock_account_after.correlative

                initial = self.env["product.product"].with_context(context).search(
                    [('type', '=', 'product'), ('qty_available', '!=', 0)])
                if product in initial:
                    saldo_inicial = product.qty_at_date,
                a = before_in.location_id.usage
                b = before_in.location_dest_id.usage
                it_code = before_in.location_id.it_establishment.code
                it_des_code = before_in.location_dest_id.it_establishment.code
                type_operation_sunat = ""
                is_scrap = before_in.location_dest_id.scrap_location

                # PRODUCCION A UNA INTERNAL TP = 19 =>ENTRADA
                if (a == "production") and (b == "internal"):
                    type_operation_sunat = "19"  # Cambiar
                    fecha = before_in.date
                    tipo_doc = "00"
                    serie = "0"
                    correlativo = "0"
                # INTERNAL A UNA PRODUCCION TP = 10 =>SALIDA
                if (a == "internal") and (b == "production"):
                    type_operation_sunat = "10"
                    fecha = before_in.date
                    tipo_doc = "00"
                    serie = "0"
                    correlativo = "0"
                # INTERNAL A UN CLIENTE TP = 01 =>SALIDA
                if (a == "internal") and (b == "customer"):
                    type_operation_sunat = "01"
                # CUSTOMER A INTERNAL ENTRADA X DEVOLUCION TP=24 => ENTRADA
                if (a == "customer") and (b == "internal"):
                    type_operation_sunat = "24"
                # INVENTORY A INTERNAL VS AJUSTES = 28 =>SALIDA
                if (a == "inventory") and (b == "internal"):
                    type_operation_sunat = "28"
                # INVENTORY A INTERNAL AJUSTES = 28 =>ENTRADA
                if (a == "internal") and (b == "inventory"):
                    type_operation_sunat = "28"
                #  INTERNAL INVENTORY IF MERMAS
                if (a == "internal") and (b == "inventory"):
                    if is_scrap is True:
                        type_operation_sunat = "13"
                #  INTERNAL INVENTORY SALIDA X DEVOLUCION TP= 25 => SALIDA
                if (a == "internal") and (b == "supplier"):
                    type_operation_sunat = "25"

                if before_in.picking_id.type_transaction.code is not False:
                    type_operation_sunat = before_in.picking_id.type_transaction.code
                # DECLARAMOS LOS CAMPOS DEL TIPO DE DOCUMENTOS PARA MOSTRAR
                if fecha is False:
                    fecha = before_in.picking_id.it_date_gr
                    if before_in.picking_id.it_date_gr is False:
                        fecha = before_in.picking_id.scheduled_date

                if before_in.picking_id.catalog_01_id.code is not False:
                    tipo_doc = before_in.picking_id.catalog_01_id.code

                if serie is False:
                    serie = before_in.picking_id.series.series
                    if before_in.picking_id.series.series is False:
                        serie = before_in.picking_id.serie

                if correlativo is False:
                    correlativo = before_in.picking_id.correlative
                    if before_in.picking_id.correlative is False:
                        correlativo = before_in.picking_id.it_correlative_manual
                if (a == 'internal') and (b != 'internal'):
                    json_stock_phisical = {
                        "type": 0,
                        "date": before_in.date,
                        "reference": before_in.reference,
                        "report_id": self.id,
                        "out_salida": before_in.product_uom_qty,
                        "product_id": before_in.product_id.id,
                        "out_saldo": before_in.price_unit * (- before_in.product_uom_qty),
                        "calculo_unit_out": before_in.price_unit,
                        # OTROS CAMPOS  PARA EL TXTSUNAT
                        "stock_id": before_in.id,
                        "establecimiento": before_in.location_id.it_establishment.code,
                        "existence": "9",
                        "codigo_propio": "6000000000000000",
                        "existence_id": before_in.product_id.it_existence.id,
                        "date_gr": fecha,
                        "catalog_01_id": tipo_doc,
                        "series": serie,
                        "correlative": correlativo,
                        "type_operation": type_operation_sunat,
                        "product_name": before_in.product_id.name,
                        "units_med": before_in.product_id.uom_id.code_unit_measure.code,

                        "cantidad_saldo_final": ((before_in.product_uom_qty) - (saldo_inicial)),
                        "costo_unit_final": before_in.price_unit,
                        "costo_total_final": (
                                    ((before_in.product_uom_qty) - (saldo_inicial)) * (before_in.price_unit)),

                    }
                    res_phisical = self.env["it.units.move.report.valuated.line"].sudo().create(json_stock_phisical)

                if (a == 'internal') and (b == 'internal') \
                        and (before_in.picking_type_id.it_is_kardex is True):
                    if (it_code is not False) and (it_des_code is False):
                        if before_in.location_id.is_kardex is False and before_in.location_dest_id.is_kardex is not True:
                            json_stock_phisical = {
                                "type": 0,
                                "date": before_in.date,
                                "reference": before_in.reference,
                                "report_id": self.id,
                                "out_salida": before_in.product_uom_qty,
                                "product_id": before_in.product_id.id,
                                "out_saldo": before_in.price_unit * (- before_in.product_uom_qty),
                                "calculo_unit_out": before_in.price_unit,
                                # OTROS CAMPOS  PARA EL TXTSUNAT
                                "stock_id": before_in.id,
                                "establecimiento": before_in.location_id.it_establishment.code,
                                "existence": "9",
                                "codigo_propio": "6000000000000000",
                                "existence_id": before_in.product_id.it_existence.id,
                                "date_gr": fecha,
                                "catalog_01_id": tipo_doc,
                                "series": serie,
                                "correlative": correlativo,
                                "type_operation": type_operation_sunat,
                                "product_name": before_in.product_id.name,
                                "units_med": before_in.product_id.uom_id.code_unit_measure.code,

                                "saldo_inicial": saldo_inicial
                            }
                            res_phisical = self.env["it.units.move.report.valuated.line"].sudo().create(
                                json_stock_phisical)
                if (a == 'internal') and (b == 'internal') \
                        and (before_in.picking_type_id.it_is_kardex is True):
                    if (it_des_code is not False) and (it_code is False):
                        if before_in.location_dest_id.is_kardex is False and before_in.location_id.is_kardex is not True:
                            json_stock_phisical = {
                                "type": 0,
                                "date": before_in.date,
                                "reference": before_in.reference,
                                "report_id": self.id,
                                "in_entrada": before_in.product_uom_qty,
                                "product_id": before_in.product_id.id,
                                "in_saldo": before_in.price_unit * before_in.product_uom_qty,
                                "calculo_unit_in": before_in.price_unit,
                                # OTROS CAMPOS  PARA EL TXTSUNAT
                                "stock_id": before_in.id,
                                "establecimiento": before_in.location_dest_id.it_establishment.code,
                                "existence": "9",
                                "codigo_propio": "6000000000000000",
                                "existence_id": before_in.product_id.it_existence.id,
                                "date_gr": fecha,
                                "catalog_01_id": tipo_doc,
                                "series": serie,
                                "correlative": correlativo,
                                "type_operation": type_operation_sunat,
                                "product_name": before_in.product_id.name,
                                "units_med": before_in.product_id.uom_id.code_unit_measure.code,

                                "saldo_inicial": saldo_inicial
                            }
                            res_phisical = self.env["it.units.move.report.valuated.line"].sudo().create(
                                json_stock_phisical)
                if (a != 'internal') and (b == 'internal'):
                    json_stock_phisical = {
                        "type": 0,
                        "date": before_in.date,
                        "reference": before_in.reference,
                        "report_id": self.id,
                        "in_entrada": before_in.product_uom_qty,
                        "product_id": before_in.product_id.id,
                        "in_saldo": before_in.price_unit * before_in.product_uom_qty,
                        "calculo_unit_in": before_in.price_unit,
                        # OTROS CAMPOS  PARA EL TXTSUNAT
                        "stock_id": before_in.id,
                        "establecimiento": before_in.location_dest_id.it_establishment.code,
                        "existence": "9",
                        "codigo_propio": "6000000000000000",
                        "existence_id": before_in.product_id.it_existence.id,
                        "date_gr": fecha,
                        "catalog_01_id": tipo_doc,
                        "series": serie,
                        "correlative": correlativo,
                        "type_operation": type_operation_sunat,
                        "product_name": before_in.product_id.name,
                        "units_med": before_in.product_id.uom_id.code_unit_measure.code,

                        "saldo_inicial": saldo_inicial,
                        "cantidad_saldo_final": round(before_in.product_uom_qty + saldo_inicial),
                        "costo_unit_final": before_in.price_unit,
                        "costo_total_final": ((before_in.product_uom_qty + saldo_inicial) * (before_in.price_unit)),
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
            stringunits = "%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s" % (
                str(d_ref.year) + "" + str(month) + "00",  # campo 1
                stock_out.stock_id,  # campo 2
                str("M") + str(stock_out.stock_id),  # campo 3
                stock_out.establecimiento or "",  # campo 4
                stock_out.catalogo_existence or "",  # campo 5
                stock_out.existence or "",  # campo 6
                stock_out.existence_id or "",  # campo 7
                stock_out.codigo_propio or "",  # campo 8
                stock_out.date_gr or "",  # campo 9
                stock_out.catalog_01_id or "",  # campo 10
                stock_out.series or "",  # campo 11
                stock_out.correlative or "",  # campo 12
                stock_out.type_operation or "",  # campo 13
                stock_out.product_name or "",  # campo 14   descripcion de la exist
                stock_out.units_med or "",  # campo 15  cod uni med
                stock_out.in_entrada or "0.00",  # campo 16 entrada
                stock_out.out_salida or "0.00",  # campo 17  salida
                "",  # campo 18
                "",  # campo 19

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
            stringvaluated = "%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s" % (
                str(d_ref.year) + "" + str(month) + "00",  # campo 1
                stock_out.stock_id,  # campo 2
                str("M") + str(stock_out.stock_id),  # campo 3
                stock_out.establecimiento or "",  # campo 4
                stock_out.catalogo_existence or "",  # campo 5
                stock_out.existence or "",  # campo 6
                stock_out.existence_id or "",  # campo 7
                stock_out.codigo_propio or "",  # campo 8
                stock_out.date_gr or "",  # campo 9
                stock_out.catalog_01_id or "",  # campo 10
                stock_out.series or "",  # campo 11
                stock_out.correlative or "",  # campo 12
                stock_out.type_operation or "",  # campo 13 tipo operacion efect
                stock_out.product_name or "",  # campo 14   descripcion de la exist
                stock_out.units_med or "",  # campo 15  cod uni med
                stock_out.in_entrada or "0.00",  # campo 16
                stock_out.in_saldo or "0.00",  # campo 17  salida
                stock_out.out_salida or "0.00",  # campo 18  salida
                stock_out.out_saldo or "0.00",  # campo 19  salida
                "",  # campo 20
                "",  # campo 21

            )
            content += str(stringvaluated) + "\r\n"

        nametxt = 'LE%s%s%s%s%s%s%s%s%s%s.TXT' % (
            self.env.user.company_id.partner_id.vat,
            d_ref.year,  # Year
            month,  # Month
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
    in_entrada = fields.Float(string="Entrada", digits=(12, 2), default=0.00)
    out_salida = fields.Float(string="Salida", digits=(12, 2), default=0.00)
    # qty_done = fields.Float(string="Cantidad")
    is_saldo = fields.Char(string="saldo inicial")
    saldo_final = fields.Float(string="Saldo Final", digits=(12, 2), default=0.00)

    # CAMPOS ADICIONALES PARA EL REPORTE DE UNIDADES FISICAS
    stock_id = fields.Char()
    establecimiento = fields.Char()
    catalogo_existence = fields.Char()
    codigo_propio = fields.Char()
    existence = fields.Char()
    existence_id = fields.Char()
    date_gr = fields.Date()
    catalog_01_id = fields.Char()
    series = fields.Char(string="Serie")
    correlative = fields.Char(string="N° Comprobante")
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
    in_entrada = fields.Float(string="Cantidad Entrada", digits=(12, 2), default=0.00)
    out_salida = fields.Float(string="Cantidad Salida", digits=(12, 2), default=0.00)
    # qty_done = fields.Float(string="Cantidad")
    is_saldo = fields.Char(string="saldo inicial", digits=(12, 2), default=0.00)
    saldo_final = fields.Float(string="Saldo Final", digits=(12, 2), default=0.00)
    # CAMPOS ADICIONALES PARA EL REPORTE DE INVENTARIO VALORIZADO
    in_saldo = fields.Float(string="Entradas Costo Total", digits=(12, 2), default=0.00, )
    out_saldo = fields.Float(string="Salida Costo Total", digits=(12, 2), default=0.00, )

    calculo_unit_in = fields.Float(string="Entradas Costo Unit.", digits=(12, 2), default=0.00)
    calculo_unit_out = fields.Float(string="Salida Costo Unit.", digits=(12, 2), default=0.00)

    cantidad_saldo_final = fields.Float(string="Cantidad Saldo Final", digits=(12, 2), default=0.00)
    costo_unit_final = fields.Float(string="Costo Unitario Saldo Final", digits=(12, 2), default=0.00)
    costo_total_final = fields.Float(string="Costo Total Saldo Final", digits=(12, 2), default=0.00)
    saldo_inicial = fields.Float()
    name_val = fields.Float(string="valor")
    existence = fields.Char(string="existence")
    # ====================================================
    stock_id = fields.Char()
    establecimiento = fields.Char()
    catalogo_existence = fields.Char()
    codigo_propio = fields.Char()
    existence_id = fields.Char()
    date_gr = fields.Char()
    catalog_01_id = fields.Char()
    series = fields.Char(string="Serie")
    correlative = fields.Char(string="N° Comprobante")
    type_operation = fields.Char()
    product_name = fields.Char()
    units_med = fields.Char()
