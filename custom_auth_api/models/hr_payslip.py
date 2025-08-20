from odoo import models, fields, api
import base64
import io
from odoo.tools.safe_eval import safe_eval

class HrPayslipInherit(models.Model):
    _inherit = 'hr.payslip'

    payslip_pdf = fields.Binary(string="Payslip PDF", readonly=True)
    payslip_pdf_filename = fields.Char(string="Payslip Filename", readonly=True)

    def compute_sheet(self):
        res = super().compute_sheet()

        for payslip in self:
            payslip._generate_and_store_pdf()

        return res

    def _generate_and_store_pdf(self):
        report_action = self.struct_id.report_id
        if not report_action:
            return

        pdf_content, _ = self.env['ir.actions.report']\
            .with_context(lang=self.employee_id.lang)\
            .sudo()\
            ._render_qweb_pdf(report_action.report_name, self.id)

        filename = report_action.print_report_name
        if filename:
            filename = safe_eval(filename, {'object': self})
        else:
            filename = f"{self.employee_id.name or 'Payslip'}.pdf"

        self.write({
            'payslip_pdf': base64.b64encode(pdf_content),
            'payslip_pdf_filename': filename,
        })
