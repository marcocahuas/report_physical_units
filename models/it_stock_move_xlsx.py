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
                stock_move_before = self.env["it.units.move.report.phisical.line"].search(
                    [("date", ">=", obj.date_in_time), ("date", "<=", obj.date_out_time)])

                array_main = []
                contador = 0
                map_products_before = {}
                for before_in in stock_move_before:
                    if before_in.product_id.id is not False:
                        str_product_id = str(before_in.product_id.id)
                        map_products_before[str_product_id]

                    array_field = []
                    array_field.append(before_in.date)
                    array_field.append(before_in.product_id.name)
                    array_field.append("")
                    array_field.append("")
                    array_field.append(before_in.date)
                    array_main.append(array_field)
                    contador = contador + 1
                sheet.set_column('A:I', 8)
                row_name = 'A8:I%s' % (int(contador + 8))
                sheet.add_table(row_name, {'data': array_main, 'columns': [{'header': 'FECHA'},
                                                                           {'header': 'Producto'},
                                                                           {'header': 'Entradas'},
                                                                           {'header': 'Salidas'},
                                                                           {'header': 'Saldo Final'},
                                                                           ]})
