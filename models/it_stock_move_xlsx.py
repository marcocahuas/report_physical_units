# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ItStockMoveReport(models.AbstractModel):
    _name = "report.report_xlsx.it.units.move.report_xlsx"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, move):
        for obj in move:
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
            # REPORTE STOCK MOVE
