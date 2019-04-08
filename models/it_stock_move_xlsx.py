# -*- coding: utf-8 -*-
from odoo import models


class ItStockMoveReport(models.AbstractModel):
    _name = "report.report_xlsx.it.units.move.report_xlsx"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, move):
        for obj in move:
            if obj.id is not False:
                # CREAR LA CABECERA
                name = 'Unidades Fisicas - %s' % ('U.F.')
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
                sheet.merge_range('A1:F4', self.env.user.company_id.name, font_titulo_empresa)
                # REPORTE STOCK MOVE UNIDADES FISICAS
                # ======================================

                # ======================================

                array_main = []
                contador = 0
                for before_in in obj.stock_phisical_lines:
                    array_field = []
                    array_field.append(before_in.date)
                    array_field.append(before_in.product_id.name)
                    array_field.append(before_in.reference)
                    array_field.append(before_in.in_entrada)
                    array_field.append(before_in.out_salida)
                    array_field.append(before_in.out_salida)
                    array_main.append(array_field)
                    contador = contador + 1
                sheet.set_column('A:F', 20)
                row_name = 'A8:F%s' % (int(contador + 8))
                sheet.add_table(row_name, {'data': array_main, 'columns': [{'header': 'FECHA'},
                                                                           {'header': 'Producto'},
                                                                           {'header': 'Referencia'},
                                                                           {'header': 'Entradas'},
                                                                           {'header': 'Salidas'},
                                                                           {'header': 'Saldo Final'},
                                                                           ]})

            # GENERAR INVENTARIO VALORIZADO
            if obj.id is not False:
                # CREAR LA CABECERA
                name = 'Inventario Valorizado - %s' % ('I.V.')
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
                sheet.merge_range('A1:G4', self.env.user.company_id.name, font_titulo_empresa)
                # REPORTE STOCK MOVE UNIDADES FISICAS
                # ======================================

                # ======================================

                array_main = []
                contador = 0
                for before_in in obj.stock_valuated_lines:
                    array_field = []
                    array_field.append(before_in.date)
                    array_field.append(before_in.product_id.name)
                    array_field.append(before_in.reference)
                    array_field.append(before_in.in_entrada)
                    array_field.append(before_in.in_saldo)
                    array_field.append(before_in.out_salida)
                    array_field.append(before_in.out_saldo)
                    array_main.append(array_field)
                    contador = contador + 1
                sheet.set_column('A:G', 20)
                row_name = 'A8:G%s' % (int(contador + 8))
                sheet.add_table(row_name, {'data': array_main, 'columns': [{'header': 'FECHA'},
                                                                           {'header': 'Producto'},
                                                                           {'header': 'Referencia'},
                                                                           {'header': 'Entradas'},
                                                                           {'header': 'In.Costo Total'},
                                                                           {'header': 'Salidas'},
                                                                           {'header': 'Out.Costo Total'},
                                                                           ]})
