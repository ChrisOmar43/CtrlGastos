from odoo import models, fields, api

class CtrlCajaConcepto(models.Model):
    _name = 'ctrl.caja.concepto'
    _description = 'Conceptos de Gasto'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Concepto', required=True, tracking=True,
                      help='Nombre del concepto de gasto')
    
    codigo = fields.Char(string='Código', tracking=True,
                        help='Código o referencia del concepto')
    
    descripcion = fields.Text(string='Descripción',
                             help='Descripción detallada del concepto')
    
    activo = fields.Boolean(string='Activo', default=True, tracking=True)
    
    # Estadísticas
    cantidad_solicitudes = fields.Integer(string='# Solicitudes', 
                                         compute='_compute_estadisticas')
    monto_total = fields.Monetary(string='Monto Total Usado',
                                  compute='_compute_estadisticas',
                                  currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Moneda',
                                  default=lambda self: self.env.company.currency_id)
    
    color = fields.Integer(string='Color', help='Color para identificación visual')
    
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Ya existe un concepto con este nombre')
    ]
    
    def _compute_estadisticas(self):
        """Calcula estadísticas de uso del concepto"""
        for rec in self:
            solicitudes = self.env['ctrl.caja.solicitud'].search([
                ('categoria_id', '=', rec.id)
            ])
            rec.cantidad_solicitudes = len(solicitudes)
            rec.monto_total = sum(solicitudes.mapped('monto_estimado'))
    
    def action_view_solicitudes(self):
        """Abre las solicitudes relacionadas con este concepto"""
        self.ensure_one()
        return {
            'name': f'Solicitudes - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ctrl.caja.solicitud',
            'view_mode': 'tree,form',
            'domain': [('categoria_id', '=', self.id)],
            'context': {'default_categoria_id': self.id}
        }