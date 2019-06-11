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
                sheet.merge_range('A1:K4', self.env.user.company_id.name, font_titulo_empresa)
                # REPORTE STOCK MOVE UNIDADES FISICAS
                # ======================================

                # ======================================

                array_main = []
                contador = 0
                for before_in in obj.stock_phisical_lines:
                    array_field = []
                    array_field.append(before_in.date)
                    array_field.append(before_in.stock_id)
                    array_field.append(before_in.establecimiento or "")
                    array_field.append(before_in.product_id.name)
                    array_field.append(before_in.reference)
                    array_field.append(before_in.series or "0")
                    array_field.append(before_in.correlative or "0")
                    array_field.append(str(before_in.type_operation)+str("-")+str(before_in.operation_name)or "")
                    array_field.append(before_in.in_entrada)
                    array_field.append(before_in.out_salida)
                    array_field.append(before_in.out_salida)
                    array_main.append(array_field)
                    contador = contador + 1
                sheet.set_column('A:K', 20)
                row_name = 'A8:K%s' % (int(contador + 8))
                sheet.add_table(row_name, {'data': array_main, 'columns': [{'header': 'FECHA'},
                                                                           {'header': 'CUO'},
                                                                           {'header': 'Establecimiento'},
                                                                           {'header': 'Producto'},
                                                                           {'header': 'Referencia'},
                                                                           {'header': 'Serie'},
                                                                           {'header': 'N° Comprobante'},
                                                                           {'header': 'Tipo Operacion'},
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
                sheet.merge_range('A1:Q4', self.env.user.company_id.name, font_titulo_empresa)
                # REPORTE STOCK MOVE UNIDADES FISICAS
                # ======================================

                # ======================================

                array_main = []
                contador = 0
                for before_in in obj.stock_valuated_lines:
                    array_field = []
                    array_field.append(before_in.date)
                    array_field.append(before_in.stock_id)
                    array_field.append(before_in.establecimiento or "")
                    array_field.append(before_in.product_id.name)
                    array_field.append(before_in.reference)
                    array_field.append(before_in.series or "0")
                    array_field.append(before_in.correlative or "0")
                    array_field.append(str(before_in.type_operation) + str("-") + str(before_in.operation_name) or "")
                    array_field.append(before_in.in_entrada)
                    array_field.append(before_in.calculo_unit_in)  # COST UNIT
                    array_field.append(before_in.in_saldo)  # COST TOTAL
                    array_field.append(before_in.out_salida)
                    array_field.append(before_in.calculo_unit_out)  # COST UNIT
                    array_field.append(before_in.out_saldo)  # SALIDA COST TOTAL
                    array_field.append(before_in.cantidad_saldo_final)  # cantidad entrada total
                    array_field.append(before_in.costo_unit_final)  # COST unitario entrada total
                    array_field.append(before_in.costo_total_final)  # saldo final total
                    array_main.append(array_field)
                    contador = contador + 1
                sheet.set_column('A:Q', 20)
                row_name = 'A8:Q%s' % (int(contador + 8))
                sheet.add_table(row_name, {'data': array_main, 'columns': [{'header': 'FECHA'},
                                                                           {'header': 'CUO'},
                                                                           {'header': 'Establecimiento'},
                                                                           {'header': 'Producto'},
                                                                           {'header': 'Referencia'},
                                                                           {'header': 'Serie'},
                                                                           {'header': 'N° Comprobante'},
                                                                           {'header': 'Tipo Operacion'},
                                                                           {'header': 'Cantidad Entradas'},
                                                                           {'header': 'Entradas Costo Unit.'},
                                                                           {'header': 'Entradas Costo Total'},
                                                                           {'header': 'Cantidad Salidas'},
                                                                           {'header': 'Salida Costo Unit.'},
                                                                           {'header': 'Salida Costo Total.'},
                                                                           {'header': 'CANTIDAD SALDO FINAL'},
                                                                           {'header': 'COSTO UNITARIO SALDO FINAL'},
                                                                           {'header': 'COSTO TOTAL SALDO FINAL'},
                                                                           ]})
