from odoo import models, fields, api

class CtrlCajaArqueo(models.Model):
    _name = 'ctrl.caja.arqueo'
    _description = 'Arqueo de Caja Chica'
    _order = 'fecha desc'

    name = fields.Char(string='Referencia', readonly=True)
    fecha = fields.Date(string='Fecha', default=fields.Date.context_today, required=True)
    mes = fields.Char(string='Mes')
    monto_caja = fields.Monetary(string='Monto esperado', currency_field='currency_id')
    monto_real = fields.Monetary(string='Monto contado', currency_field='currency_id')
    diferencia = fields.Monetary(string='Diferencia', compute='_compute_diferencia', store=True, currency_field='currency_id')
    accion = fields.Text(string='Acción tomada')
    realizo_id = fields.Many2one('hr.employee', string='Realizó')
    reviso_id = fields.Many2one('hr.employee', string='Revisó')
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self: self.env.company.currency_id)

    gastos_ids = fields.One2many('ctrl.caja.chica','arqueo_id', string='Gastos vinculados')

    @api.depends('monto_caja','monto_real')
    def _compute_diferencia(self):
        for rec in self:
            rec.diferencia = (rec.monto_caja or 0.0) - (rec.monto_real or 0.0)

    @api.model
    def create(self, vals):
        vals['name'] = vals.get('name') or self.env['ir.sequence'].next_by_code('ctrl.caja.arqueo') or '/'
        return super().create(vals)
