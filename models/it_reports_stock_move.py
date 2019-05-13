# -*- coding: utf-8 -*-

import base64
import datetime
import logging

from mock.mock import self
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
    establishment = fields.Many2one('it.stock.warehouse', string='Establecimiento')
    locas = fields.Char()
    txt_filename = fields.Char()
    txt_binary = fields.Binary(string='Descargar Txt Sunat')
    # stock_move_lines = fields.Many2many(comodel_name="stock.move.line", string="Movimientos", ondelete="cascade")
    stock_phisical_lines = fields.One2many('it.units.move.report.phisical.line', 'report_id',
                                           string="Kardex",
                                           ondelete="cascade")
    stock_valuated_lines = fields.One2many('it.units.move.report.valuated.line', 'report_id',
                                           string="Kardex",
                                           ondelete="cascade")

    # @api.multi
    # @api.onchange('code')
    # def establishment_id_change(self):
    #     res = super(ItStockMoveReport, self).establishment_id_change()
    #     if self.code:
    #         lot_id = self.env['it.stock.warehouse'].search([('code', '=', self.establishment.id)], limit=1,
    #                                                          order="name")
    #         if lot_id:
    #             self.establishment = lot_id.id
    #     return res

    @api.multi
    def unlink(self):
        for item_report in self:
            if item_report.stock_phisical_lines:
                item_report.stock_phisical_lines.unlink()
            if item_report.stock_valuated_lines:
                item_report.stock_valuated_lines.unlink()
        res = super(ItStockMoveReport, self).unlink()
        return res

    @api.onchange("business_name")
    def _compute_it_ruc(self):
        self.vat = self.business_name.partner_id.vat or ""

    # @api.one
    # def stablish(self):
    #     estable = filter(lambda establishment: establishment.code = "=", "establecimiento")
    #     for menor in menores:
    #         print(menor

    # @api.onchange("code")
    # def change_establishment(self):
    #     estable = self.establishment.code
    #     if self.estable is not False:
    #         inv_suppliers = self.env["it.units.move.report.phisical.line"].search(
    #             [('establecimiento', '=', estable)])
    #         for inv in inv_suppliers:
    #             if inv.code == estable:
    #                 pass

    @api.one
    def _compute_it_sunat_sale(self):
        type_op = self.env["it.units.move.report.phisical.line"].search([('establecimiento', '=', self.establishment.code)])
        if type_op.id is not False:
            self.locas = type_op.id

    # @api.onchange
    # def get_journals(cr, uid, context=None):
    #     journal_obj = self.pool.get('it.stock.warehouse')
    #     journal_ids = journal_obj.search(cr, uid, [], context=context)
    #     lst = []
    #     for journal in journal_obj.browse(cr, uid, journal_ids, context=context):
    #         lst.append((journal.code, journal.name))
    #     return lst
    #
    # _columns = {
    #     'selection': fields.selection(get_journals, string='Selection'),
    # }
    # def _default_it_cod_ope_ley(self):
    #     self.estable = self.env["it.stock.warehouse"].search([('code', '=', self.establishment.code)])
    #     return self.estable.code

    @api.one
    def generate_moves(self):
        if self.stock_phisical_lines:
            self.stock_phisical_lines.unlink()

        type_op = self.env["it.units.move.report.phisical.line"].search(
            [('establecimiento', '=', self.establishment.code)]).code
        self.locas = type_op

        d_ref = datetime.datetime.strptime(self.date_out, "%Y-%m-%d")
        d_ref_out = datetime.datetime.strptime(self.date_out, "%Y-%m-%d")
        d_ref_in = datetime.datetime.strptime(self.date_in, "%Y-%m-%d")
        month = "%02d" % (d_ref.month,)
        # DECLARAR FECHAS
        date_in_before = datetime.datetime.combine(datetime.date(d_ref_in.year, d_ref_in.month, d_ref_in.day),
                                                   datetime.time(0, 0, 0))
        date_out_after = datetime.datetime.combine(datetime.date(d_ref_out.year, d_ref_out.month, d_ref_out.day),
                                                   datetime.time(23, 59, 59))
        self.date_in_time = date_in_before
        self.date_out_time = date_out_after
        # --------------------------------------------------
        # establecimiento = self.env["it.stock.warehouse"].search([('code', '=', self.establishment.code)])
        #
        context = {'to_date': self.date_in_time}
        initial = self.env["product.product"].with_context(context).search(
            [('type', '=', 'product'), ('qty_available', '!=', 0)])

        res_operacion = self.env["type.of.operation"]
        code_transaction = "16"
        description_transaction = res_operacion.search(
            [("code", "=", code_transaction)], limit=1).description

        for product in initial:

            map_stabl = {}
            for stock_quant in product.stock_quant_ids:
                if stock_quant.location_id.it_establishment.id:
                    if stock_quant.location_id.it_establishment.code not in map_stabl:
                        map_stabl[stock_quant.location_id.it_establishment.code] = 0
                    value_stock = map_stabl[stock_quant.location_id.it_establishment.code]
                    value_stock = value_stock + stock_quant.quantity
                    map_stabl[stock_quant.location_id.it_establishment.code] = value_stock

            for code_estbl, quantity_total in map_stabl.items():
                json_stock_phisical = {
                    "type": 1,
                    "date": self.date_in_time,
                    "reference": "SALDO INICIAL",
                    "is_saldo": "AAAA",
                    "in_entrada": quantity_total,
                    "report_id": self.id,
                    "product_id": product.id,
                    # campos adicionales
                    "stock_id": product.id,
                    "establecimiento": code_estbl,
                    "catalogo_existence": "9",
                    "existence_id": "OTROS",
                    "codigo_propio": "6000000000000000",
                    "type_operation": code_transaction,
                    "operation_name": description_transaction,
                    "product_name": product.name,
                    "date_gr": self.date_in_time,
                    "catalog_01_id": "00",
                    "series": "0",
                    "correlative": "0",
                    "existence": product.it_existence.code,
                    "units_med": product.uom_id.code_unit_measure.code
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

                # CAMPOS PARA IN OR OUT DE MOMIENTOS DE STOCK_MOVE
                a = before_in.location_id.usage
                b = before_in.location_dest_id.usage
                it_code = before_in.location_id.it_establishment.code
                it_des_code = before_in.location_dest_id.it_establishment.code

                is_scrap = before_in.location_dest_id.scrap_location
                code_transaction = False
                description_transaction = False
                # VALORES YA ASIGNADOS
                if before_in.picking_id.id:
                    if before_in.picking_id.type_transaction.id:
                        code_transaction = before_in.picking_id.type_transaction.code
                        description_transaction = before_in.picking_id.type_transaction.description

                # HARDCODING

                if code_transaction is False:
                    res_operacion = self.env["type.of.operation"]
                    # PRODUCCION A UNA INTERNAL TP = 19 =>ENTRADA
                    if (a == "production") and (b == "internal"):
                        code_transaction = "19"
                        description_transaction = res_operacion.search(
                            [("code", "=", code_transaction)], limit=1).description
                        fecha = before_in.date
                        tipo_doc = "00"
                        serie = "0"
                        correlativo = "0"
                    # INTERNAL A UNA PRODUCCION TP = 10 =>SALIDA
                    if (a == "internal") and (b == "production"):
                        code_transaction = "10"
                        description_transaction = res_operacion.search(
                            [("code", "=", code_transaction)], limit=1).description
                        fecha = before_in.date
                        tipo_doc = "00"
                        serie = "0"
                        correlativo = "0"
                    # INTERNAL A UN CLIENTE TP = 01 =>SALIDA
                    if (a == "internal") and (b == "customer"):
                        code_transaction = "01"
                        description_transaction = res_operacion.search(
                            [("code", "=", code_transaction)], limit=1).description
                    # CUSTOMER A INTERNAL ENTRADA X DEVOLUCION TP=24 => ENTRADA
                    if (a == "customer") and (b == "internal"):
                        code_transaction = "24"
                        description_transaction = res_operacion.search(
                            [("code", "=", code_transaction)], limit=1).description
                    # INVENTORY A INTERNAL VS AJUSTES = 28 =>SALIDA
                    if (a == "inventory") and (b == "internal"):
                        code_transaction = "28"
                        description_transaction = res_operacion.search(
                            [("code", "=", code_transaction)], limit=1).description
                    # INVENTORY A INTERNAL VS AJUSTES = 28 =>SALIDA
                    if (a == "internal") and (b == "inventory"):
                        code_transaction = "28"
                        description_transaction = res_operacion.search(
                            [("code", "=", code_transaction)], limit=1).description
                    #  INTERNAL INVENTORY IF MERMAS
                    if (a == "internal") and (b == "inventory") and is_scrap is True:
                        code_transaction = "13"
                        description_transaction = res_operacion.search(
                            [("code", "=", code_transaction)], limit=1).description
                    #  INTERNAL INVENTORY IF MERMAS
                    if (a == "internal") and (b == "supplier"):
                        code_transaction = "25"
                        description_transaction = res_operacion.search(
                            [("code", "=", code_transaction)], limit=1).description

                # INTERNAL A PRODUCTION DESECHOS TP=99 => SALIDA
                # if (a == "internal") and (b == "production"):
                #     if before_in.location_id.is_kardex is True:
                #         type_operation_sunat = "99"  # falta analizar


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

                # # Ajuste
                # ajuste_fiscal = "0"
                # date_comprobante = datetime.datetime.strptime(before_in.date, "%Y-%m-%d")
                # mes_comprobante = str(date_comprobante.year) + "" + str("%02d" % (date_comprobante.month))
                # mes_actual = str(d_ref.year) + "" + str(month)
                # if before_in.picking_id.catalog_01_id.code == "01" or before_in.picking_id.catalog_01_id.code == "07":
                #     ajuste_fiscal = "1"
                #     if mes_actual != mes_comprobante:
                #         ajuste_fiscal = "6"
                # if before_in.picking_id.catalog_01_id.code == "03":
                #     if mes_actual != mes_comprobante:
                #         ajuste_fiscal = "7"

                if (a == 'internal') and (b != 'internal'):
                    json_stock_phisical = {
                        "type": 0,
                        "date": before_in.date,
                        "reference": before_in.reference,
                        "report_id": self.id,
                        "out_salida": - before_in.product_uom_qty,
                        "product_id": before_in.product_id.id,
                        # OTROS CAMPOS  PARA EL TXTSUNAT
                        "stock_id": before_in.account_move_ids.id,
                        "establecimiento": before_in.location_id.it_establishment.code,
                        "catalogo_existence": "9",
                        "codigo_propio": "6000000000000000",
                        "existence": before_in.product_id.it_existence.code,
                        "existence_id": "OTROS",
                        "date_gr": fecha,
                        "catalog_01_id": tipo_doc,
                        "series": serie,
                        "correlative": correlativo,
                        "type_operation": code_transaction,
                        "operation_name": description_transaction,
                        "product_name": before_in.product_id.name,
                        "units_med": before_in.product_id.uom_id.code_unit_measure.code,
                        # "ajuste_fiscal": ajuste_fiscal
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
                                "out_salida": - before_in.product_uom_qty,
                                "product_id": before_in.product_id.id,
                                # OTROS CAMPOS  PARA EL TXTSUNAT
                                "stock_id": before_in.account_move_ids.id,
                                "establecimiento": before_in.location_id.it_establishment.code,
                                "catalogo_existence": "9",
                                "codigo_propio": "6000000000000000",
                                "existence": before_in.product_id.it_existence.code,
                                "existence_id": "OTROS",
                                "date_gr": fecha,
                                "catalog_01_id": tipo_doc,
                                "series": serie,
                                "correlative": correlativo,
                                "type_operation": code_transaction,
                                "operation_name": description_transaction,
                                "product_name": before_in.product_id.name,
                                "units_med": before_in.product_id.uom_id.code_unit_measure.code,
                                # "ajuste_fiscal": ajuste_fiscal
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
                                "stock_id": before_in.account_move_ids.id,
                                "establecimiento": before_in.location_dest_id.it_establishment.code,
                                "catalogo_existence": "9",
                                "codigo_propio": "6000000000000000",
                                "existence": before_in.product_id.it_existence.code,
                                "existence_id": "OTROS",
                                "date_gr": fecha,
                                "catalog_01_id": tipo_doc,
                                "series": serie,
                                "correlative": correlativo,
                                "type_operation": code_transaction,
                                "operation_name": description_transaction,
                                "product_name": before_in.product_id.name,
                                "units_med": before_in.product_id.uom_id.code_unit_measure.code,
                                # "ajuste_fiscal": ajuste_fiscal
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
                        "stock_id": before_in.account_move_ids.id,
                        "establecimiento": before_in.location_dest_id.it_establishment.code,
                        "catalogo_existence": "9",
                        "codigo_propio": "6000000000000000",
                        "existence": before_in.product_id.it_existence.code,
                        "existence_id": "OTROS",
                        "date_gr": fecha,
                        "catalog_01_id": tipo_doc,
                        "series": serie,
                        "correlative": correlativo,
                        "type_operation": code_transaction,
                        "operation_name": description_transaction,
                        "product_name": before_in.product_id.name,
                        "units_med": before_in.product_id.uom_id.code_unit_measure.code,
                        # "ajuste_fiscal": ajuste_fiscal
                    }
                    res_phisical = self.env["it.units.move.report.phisical.line"].sudo().create(json_stock_phisical)

        #  ====================================================================================================
        #  REPORTE DE INVENTARIO VALORIZADO
        #  ====================================================================================================
        # OBTENEMOS EL SALDO INICIAL
        context = {'to_date': self.date_in_time}
        initial = self.env["product.product"].with_context(context).search(
            [('type', '=', 'product'), ('qty_available', '!=', 0)])
        res_operacion = self.env["type.of.operation"]
        code_transaction = "16"
        description_transaction = res_operacion.search(
            [("code", "=", code_transaction)], limit=1).description

        for product in initial:
            metodo_coste = ""
            if product.categ_id.property_cost_method == "average":
                metodo_coste = "1"
            if product.categ_id.property_cost_method == "fifo":
                metodo_coste = "2"
            if product.categ_id.property_cost_method == "standard":
                metodo_coste = "3"
            map_stabl = {}
            for stock_quant in product.stock_quant_ids:
                if stock_quant.location_id.it_establishment.id:
                    if stock_quant.location_id.it_establishment.code not in map_stabl:
                        map_stabl[stock_quant.location_id.it_establishment.code] = 0
                    value_stock = map_stabl[stock_quant.location_id.it_establishment.code]
                    value_stock = value_stock + stock_quant.quantity
                    map_stabl[stock_quant.location_id.it_establishment.code] = value_stock
            for code_estbl, quantity_total in map_stabl.items():
                json_stock_phisical = {
                    "type": 1,
                    "date": self.date_in_time,
                    "reference": "SALDO INICIAL",
                    "is_saldo": "AAAA",
                    "in_entrada": quantity_total,
                    "report_id": self.id,
                    "product_id": product.id,
                    # campos adicionales
                    "stock_id": product.id,
                    "establecimiento": code_estbl,
                    "catalogo_existence": "9",
                    "existence_id": "OTROS",
                    "codigo_propio": "6000000000000000",
                    "type_operation": code_transaction,
                    "operation_name": description_transaction,
                    "product_name": product.name,
                    "date_gr": self.date_in_time,
                    "catalog_01_id": "00",
                    "series": "0",
                    "correlative": "0",
                    "existence": product.it_existence.code,
                    "units_med": product.uom_id.code_unit_measure.code,
                    "metodo_valuacion": metodo_coste,
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
            [("date", ">=", self.date_in_time), ("date", "<=", self.date_out_time), ('user_type_id', '=', 5),
             ('journal_id', '=', 6), '|', ('quantity', '=', False), ('quantity', '=', 0)])
        code_transaction = "99"
        description_transaction = "DECONSTRUCCIÓN"
        # description_transaction = res_operacion.search(
        #     [("code", "=", code_transaction)], limit=1).description
        for valor in entry_balance:
            # PARA EL PRECIO UNIT SALDO FINAL
            saldo_price_unit = self.env["it.units.move.report.valuated.line"].search(
                [("product_id", "=", valor.product_id.id), ("type", "=", 0)], limit=1)
            saldo_unit = False
            if saldo_price_unit.costo_total_final != 0 and saldo_price_unit.cantidad_saldo_final != 0:
                saldo_unit = saldo_price_unit.costo_total_final / saldo_price_unit.cantidad_saldo_final
            metodo_coste = ""
            if valor.product_id.categ_id.property_cost_method == "average":
                metodo_coste = "1"
            if valor.product_id.categ_id.property_cost_method == "fifo":
                metodo_coste = "2"
            if valor.product_id.categ_id.property_cost_method == "standard":
                metodo_coste = "3"

            # PARA EL COSTO FINAL SE OBTIENE DEL VALORIZADO
            costo_final = False
            cantidad_saldo = False
            #establesh = False
            if valor.date:
                context_finally = {'to_date': valor.date}
                costo_finaly = self.env["product.product"].with_context(context_finally).search(
                    [('id', '=', valor.product_id.id), ('type', '=', 'product')], limit=1)
                if costo_finaly.id:
                    costo_final = costo_finaly.stock_value
                    cantidad_saldo = costo_finaly.qty_at_date

                _logger.info("COSTO FINAL")
                _logger.info(costo_finaly.qty_at_date)
                map_stabl = {}
                for stock_quant in costo_finaly.stock_quant_ids:
                    if stock_quant.location_id.it_establishment.id:
                        if stock_quant.location_id.it_establishment.code not in map_stabl:
                            map_stabl[stock_quant.location_id.it_establishment.code] = 0
                        value_stock = map_stabl[stock_quant.location_id.it_establishment.code]
                        #value_stock = value_stock + stock_quant.quantity
                        map_stabl[stock_quant.location_id.it_establishment.code] = value_stock
                for code_estbl in map_stabl.items():
                    json_stock_phisical = {
                        "date": valor.create_date,
                        "in_saldo": valor.debit,
                        "out_saldo": valor.credit,
                        "reference": "AJUSTE DE COSTOS",
                        "report_id": self.id,
                        "product_id": valor.product_id.id,
                        "calculo_unit_out": "0.00",
                        # campos adicionales
                        "catalogo_existence": "9",
                        "establecimiento": code_estbl,
                        "existence_id": "OTROS",
                        "codigo_propio": "6000000000000000",
                        "type_operation": code_transaction,
                        "operation_name": description_transaction,
                        "product_name": valor.product_id.name,
                        "date_gr": self.date_in_time,
                        "catalog_01_id": "00",
                        "series": "0",
                        "correlative": "0",
                        "existence": valor.product_id.it_existence.code,
                        "stock_id": valor.move_id.id,
                        "units_med": valor.product_id.uom_id.code_unit_measure.code,
                        "metodo_valuacion": metodo_coste,  # valor.product_id.categ_id.name
                        "cantidad_saldo_final": cantidad_saldo,
                        "costo_unit_final": saldo_unit,
                        "costo_total_final": costo_final,
                    }
                    res_phisical = self.env["it.units.move.report.valuated.line"].sudo().create(json_stock_phisical)

        # OBTENEMOS LOS MOVIMIENTOS DE STOCK MOVE
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

                # PARA EL COSTO FINAL SE OBTIENE DEL VALORIZADO
                costo_final = False
                cantidad_saldo = False
                if before_in.date:
                    context_finally = {'to_date': before_in.date}
                    costo_finaly = self.env["product.product"].with_context(context_finally).search(
                        [('id', '=', before_in.product_id.id),
                         ('type', '=', 'product')], limit=1)
                    if costo_finaly.id:
                        costo_final = costo_finaly.stock_value
                        cantidad_saldo = costo_finaly.qty_at_date
                    _logger.info("COSTO FINAL")
                    _logger.info(costo_finaly.qty_at_date)

                # PARA EL PRECIO UNIT SALDO FINAL
                saldo_price_unit = self.env["it.units.move.report.valuated.line"].search(
                    [("product_id", "=", before_in.product_id.id), ("type", "=", 0)], limit=1)
                saldo_unit = False
                if saldo_price_unit.costo_total_final != 0 and saldo_price_unit.cantidad_saldo_final != 0:
                    saldo_unit = saldo_price_unit.costo_total_final / saldo_price_unit.cantidad_saldo_final

                # PARA LOS MOVIMIENTOS DE STOCK_MOVE
                a = before_in.location_id.usage
                b = before_in.location_dest_id.usage
                it_code = before_in.location_id.it_establishment.code
                it_des_code = before_in.location_dest_id.it_establishment.code
                type_operation_sunat = ""
                type_operation_name = ""
                metodo_coste = ""
                is_scrap = before_in.location_dest_id.scrap_location

                if before_in.product_id.categ_id.property_cost_method == "average":
                    metodo_coste = "1"
                if before_in.product_id.categ_id.property_cost_method == "fifo":
                    metodo_coste = "2"
                if before_in.product_id.categ_id.property_cost_method == "standard":
                    metodo_coste = "3"

                code_transaction = False
                description_transaction = False
                # VALORES YA ASIGNADOS
                if before_in.picking_id.id:
                    if before_in.picking_id.type_transaction.id:
                        code_transaction = before_in.picking_id.type_transaction.code
                        description_transaction = before_in.picking_id.type_transaction.description

                # HARDCODING

                if code_transaction is False:
                    res_operacion = self.env["type.of.operation"]
                    # PRODUCCION A UNA INTERNAL TP = 19 =>ENTRADA
                    if (a == "production") and (b == "internal"):
                        code_transaction = "19"
                        description_transaction = res_operacion.search(
                            [("code", "=", code_transaction)], limit=1).description
                        fecha = before_in.date
                        tipo_doc = "00"
                        serie = "0"
                        correlativo = "0"
                    # INTERNAL A UNA PRODUCCION TP = 10 =>SALIDA
                    if (a == "internal") and (b == "production"):
                        code_transaction = "10"
                        description_transaction = res_operacion.search(
                            [("code", "=", code_transaction)], limit=1).description
                        fecha = before_in.date
                        tipo_doc = "00"
                        serie = "0"
                        correlativo = "0"
                    # INTERNAL A UN CLIENTE TP = 01 =>SALIDA
                    if (a == "internal") and (b == "customer"):
                        code_transaction = "01"
                        description_transaction = res_operacion.search(
                            [("code", "=", code_transaction)], limit=1).description
                    # CUSTOMER A INTERNAL ENTRADA X DEVOLUCION TP=24 => ENTRADA
                    if (a == "customer") and (b == "internal"):
                        code_transaction = "24"
                        description_transaction = res_operacion.search(
                            [("code", "=", code_transaction)], limit=1).description
                    # INVENTORY A INTERNAL VS AJUSTES = 28 =>SALIDA
                    if (a == "inventory") and (b == "internal"):
                        code_transaction = "28"
                        description_transaction = res_operacion.search(
                            [("code", "=", code_transaction)], limit=1).description
                    # INVENTORY A INTERNAL VS AJUSTES = 28 =>SALIDA
                    if (a == "internal") and (b == "inventory"):
                        code_transaction = "28"
                        description_transaction = res_operacion.search(
                            [("code", "=", code_transaction)], limit=1).description
                    #  INTERNAL INVENTORY IF MERMAS
                    if (a == "internal") and (b == "inventory") and is_scrap is True:
                        code_transaction = "13"
                        description_transaction = res_operacion.search(
                            [("code", "=", code_transaction)], limit=1).description
                    #  INTERNAL INVENTORY IF MERMAS
                    if (a == "internal") and (b == "supplier"):
                        code_transaction = "25"
                        description_transaction = res_operacion.search(
                            [("code", "=", code_transaction)], limit=1).description


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
                        "calculo_unit_out": (- before_in.price_unit),
                        # OTROS CAMPOS  PARA EL TXTSUNAT
                        "stock_id": before_in.account_move_ids.id,
                        "establecimiento": before_in.location_id.it_establishment.code,
                        "catalogo_existence": "9",
                        "existence": before_in.product_id.it_existence.code,
                        "codigo_propio": "6000000000000000",
                        "existence_id": "OTROS",
                        "date_gr": fecha,
                        "catalog_01_id": tipo_doc,
                        "series": serie,
                        "correlative": correlativo,
                        "type_operation": code_transaction,
                        "operation_name": description_transaction,
                        "product_name": before_in.product_id.name,
                        "units_med": before_in.product_id.uom_id.code_unit_measure.code,
                        "metodo_valuacion": metodo_coste,
                        "cantidad_saldo_final": cantidad_saldo,
                        "costo_unit_final": saldo_unit,
                        "costo_total_final": costo_final,

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
                                "calculo_unit_out": (- before_in.price_unit),
                                # OTROS CAMPOS  PARA EL TXTSUNAT
                                "stock_id": before_in.account_move_ids.id,
                                "establecimiento": before_in.location_id.it_establishment.code,
                                "catalogo_existence": "9",
                                "existence": before_in.product_id.it_existence.code,
                                "codigo_propio": "6000000000000000",
                                "existence_id": "OTROS",
                                "date_gr": fecha,
                                "catalog_01_id": tipo_doc,
                                "series": serie,
                                "correlative": correlativo,
                                "type_operation": code_transaction,
                                "operation_name": description_transaction,
                                "product_name": before_in.product_id.name,
                                "units_med": before_in.product_id.uom_id.code_unit_measure.code,
                                "metodo_valuacion": metodo_coste,
                                "cantidad_saldo_final": cantidad_saldo,
                                "costo_unit_final": saldo_unit,
                                "costo_total_final": costo_final,

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
                                "stock_id": before_in.account_move_ids.id,
                                "establecimiento": before_in.location_dest_id.it_establishment.code,
                                "catalogo_existence": "9",
                                "existence": before_in.product_id.it_existence.code,
                                "codigo_propio": "6000000000000000",
                                "existence_id": "OTROS",
                                "date_gr": fecha,
                                "catalog_01_id": tipo_doc,
                                "series": serie,
                                "correlative": correlativo,
                                "type_operation": code_transaction,
                                "operation_name": description_transaction,
                                "product_name": before_in.product_id.name,
                                "units_med": before_in.product_id.uom_id.code_unit_measure.code,
                                "metodo_valuacion": metodo_coste,
                                "cantidad_saldo_final": cantidad_saldo,
                                "costo_unit_final": saldo_unit,
                                "costo_total_final": costo_final,

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
                        "stock_id": before_in.account_move_ids.id,
                        "establecimiento": before_in.location_dest_id.it_establishment.code,
                        "catalogo_existence": "9",
                        "existence": before_in.product_id.it_existence.code,
                        "codigo_propio": "6000000000000000",
                        "existence_id": "OTROS",
                        "date_gr": fecha,
                        "catalog_01_id": tipo_doc,
                        "series": serie,
                        "correlative": correlativo,
                        "type_operation": code_transaction,
                        "operation_name": description_transaction,
                        "product_name": before_in.product_id.name,
                        "units_med": before_in.product_id.uom_id.code_unit_measure.code,
                        "metodo_valuacion": metodo_coste,
                        "cantidad_saldo_final": cantidad_saldo,
                        "costo_unit_final": saldo_unit,
                        "costo_total_final": costo_final,
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
        date_gr = ""
        for stock_out in self.stock_phisical_lines:
            count_sale = 1
            if stock_out.date_gr is not False:
                fecha2 = datetime.datetime.strptime(stock_out.date_gr, "%Y-%m-%d")
                date_gr = "%02d" % (fecha2.day) + "/" + "%02d" % (fecha2.month) + "/" + str(
                    fecha2.year)
            stringunits = "%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|" % (
                str(d_ref.year) + "" + str(month) + "00",  # campo 1
                stock_out.stock_id,  # campo 2
                str("M") + str(stock_out.stock_id),  # campo 3
                stock_out.establecimiento or "",  # campo 4
                stock_out.catalogo_existence or "",  # campo 5
                stock_out.existence or "",  # campo 6
                stock_out.existence_id or "",  # campo 7
                stock_out.codigo_propio or "",  # campo 8
                date_gr or "",  # campo 9
                stock_out.catalog_01_id or "",  # campo 10
                stock_out.series or "",  # campo 11
                stock_out.correlative or "",  # campo 12
                stock_out.type_operation or "",  # campo 13
                stock_out.product_name or "",  # campo 14   descripcion de la exist
                stock_out.units_med or "",  # campo 15  cod uni med
                "%.2f" % round(stock_out.in_entrada, 2) or "0.00",  # campo 16 entrada
                "%.2f" % round(stock_out.out_salida, 2) or "0.00",  # campo 17  salida
                "1",  # Estado
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
        date_gr = ""
        for stock_out in self.stock_valuated_lines:
            count_sale = 1
            if stock_out.date_gr is not False:
                fecha2 = datetime.datetime.strptime(stock_out.date_gr, "%Y-%m-%d")
                date_gr = "%02d" % (fecha2.day) + "/" + "%02d" % (fecha2.month) + "/" + str(
                    fecha2.year)
            stringvaluated = "%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|" % (
                str(d_ref.year) + "" + str(month) + "00",  # campo 1
                stock_out.stock_id,  # campo 2
                str("M") + str(stock_out.stock_id),  # campo 3
                stock_out.establecimiento or "",  # campo 4
                stock_out.catalogo_existence or "",  # campo 5
                stock_out.existence or "",  # campo 6
                stock_out.existence_id or "",  # campo 7
                stock_out.codigo_propio or "",  # campo 8
                date_gr or "",  # campo 9
                stock_out.catalog_01_id or "",  # campo 10
                stock_out.series or "",  # campo 11
                stock_out.correlative or "",  # campo 12
                stock_out.type_operation or "",  # campo 13 tipo operacion efect
                stock_out.product_name or "",  # campo 14   descripcion de la exist
                stock_out.units_med or "",  # campo 15  cod uni med
                stock_out.metodo_valuacion or "",
                "%.2f" % round(stock_out.in_entrada, 2) or "0.00",  # campo 16 cantidad entrada
                "%.2f" % round(stock_out.calculo_unit_in, 2) or "0.00",  # 17ENTRADA DEL COSTO UNITARIO
                "%.2f" % round(stock_out.in_saldo, 2) or "0.00",  # campo 18  ENTRADA del costo total
                "%.2f" % round(stock_out.out_salida, 2) or "0.00",  # campo 19  cantidad de salida
                "%.2f" % round(stock_out.calculo_unit_out, 2) or "0.00",  # 20 SALIDA DE COSTO UNITARIO
                "%.2f" % round(stock_out.out_saldo, 2) or "0.00",  # 21 SALIDA DEL COSTO TOTAL
                "%.2f" % round(stock_out.cantidad_saldo_final, 2) or "0.00",  # 22 CANTIDAD DE SALDO FINAL
                "%.2f" % round(stock_out.costo_unit_final, 2) or "0.00",  # 23 COSTO UNITARIO DEL SALDO FINAL
                "%.2f" % round(stock_out.costo_total_final, 2) or "0.00",  # 24 COSTO DEL SALDO FINAL
                "1",  # campo 25  ESTADO
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
    operation_name = fields.Char()
    product_name = fields.Char()
    units_med = fields.Char()
    # ajuste_fiscal = fields.Char()


class ItStockMoveReportValuatedLine(models.Model):
    _name = "it.units.move.report.valuated.line"
    _description = "Reporte Inventario Valorizado Detalle"
    _order = "product_name, date asc"

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
    saldo_inicial = fields.Float(string="Cantidad Saldo Final", digits=(12, 2), default=0.00)
    # ====================================================
    stock_id = fields.Char()
    establecimiento = fields.Char()
    catalogo_existence = fields.Char()
    codigo_propio = fields.Char()
    existence_id = fields.Char()
    date_gr = fields.Date()
    catalog_01_id = fields.Char()
    series = fields.Char(string="Serie")
    correlative = fields.Char(string="N° Comprobante")
    type_operation = fields.Char()
    operation_name = fields.Char()
    product_name = fields.Char()
    units_med = fields.Char()
    metodo_valuacion = fields.Char()
