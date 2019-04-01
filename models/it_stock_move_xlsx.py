# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ItStockMoveReport(models.AbstractModel):
    _name = "report.report_xlsx.it.units.move.report_xlsx"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, move):
        for obj in move:
            if obj.id is not False:
                # CREAR LA CABECERA
                name = 'Inventario Valorizado - %s' % (obj.business_name)
                sheet = workbook.add_worksheet(name)
                font_titulo_empresa = workbook.add_format(
                    {
                        'bold': True,
                        'font_color': '#0B173B',
                        'font_size': 14,
                        'border': 4,
                        'align': 'center',
                        'valign': 'vcenter'
                    })
                sheet.merge_range('A1:I4', self.env.user.company_id.name, font_titulo_empresa)
                # REPORTE STOCK MOVE UNIDADES FISICAS
                #======================================
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
                        "product_id": product.id
                    }
                    res_phisical = self.env["it.units.move.report.phisical.line"].sudo().create(json_stock_phisical)

                # GENERAR LOS MOVIMIENTOS:

                stock_move_after = self.env["stock.move.line"].search(
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
                                "out_salida": before_in.qty_done,
                                "product_id": before_in.product_id.id
                            }
                            res_phisical = self.env["it.units.move.report.phisical.line"].sudo().create(
                                json_stock_phisical)

                        if (a == 'internal') and (b == 'internal'):
                            # PENDIENTE MOVIMIENTO ENTRE ALMACENES QUE VAN AL ESTE REPORTE
                            pass
                        if (a != 'internal') and (b == 'internal'):
                            json_stock_phisical = {
                                "type": 0,
                                "date": before_in.date,
                                "reference": before_in.reference,
                                "report_id": self.id,
                                "in_entrada": before_in.qty_done,
                                "product_id": before_in.product_id.id
                            }
                            res_phisical = self.env["it.units.move.report.phisical.line"].sudo().create(
                                json_stock_phisical)
                #======================================
                stock_move_before = self.env["it.units.move.report.phisical.line"].search(
                    [("date", ">=", obj.date_in_time), ("date", "<=", obj.date_out_time)])

                array_main = []
                contador = 0
                for before_in in stock_move_before:
                    array_field = []
                    array_field.append(before_in.date)
                    array_field.append(before_in.product_id.name)
                    array_field.append(before_in.reference)
                    array_field.append(before_in.in_entrada)
                    array_field.append(before_in.out_salida)
                    array_field.append(before_in.date)
                    array_main.append(array_field)
                    contador = contador + 1
                sheet.set_column('A:I', 8)
                row_name = 'A8:I%s' % (int(contador + 8))
                sheet.add_table(row_name, {'data': array_main, 'columns': [{'header': 'FECHA'},
                                                                           {'header': 'Producto'},
                                                                           {'header': 'Referencia'},
                                                                           {'header': 'Entradas'},
                                                                           {'header': 'Salidas'},
                                                                           {'header': 'Saldo Final'},
                                                                           ]})
