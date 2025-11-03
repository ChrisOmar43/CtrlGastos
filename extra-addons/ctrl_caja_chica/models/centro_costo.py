from odoo import models, fields, api

class CtrlCajaCentroCosto(models.Model):
    _name = 'ctrl.caja.centro.costo'
    _description = 'Centros de Costo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'codigo, name'

    name = fields.Char(string='Centro de Costo', required=True, tracking=True,
                      help='Nombre del centro de costo')
    
    codigo = fields.Char(string='Código', required=True, tracking=True,
                        help='Código del centro de costo (ej: ALM, ADMIN)')
    
    descripcion = fields.Text(string='Descripción',
                             help='Descripción del centro de costo')
    
    responsable_id = fields.Many2one('hr.employee', string='Responsable',
                                    tracking=True,
                                    help='Responsable del centro de costo')
    
    activo = fields.Boolean(string='Activo', default=True, tracking=True)
    
    # Estadísticas
    cantidad_solicitudes = fields.Integer(string='# Solicitudes',
                                         compute='_compute_estadisticas')
    monto_total = fields.Monetary(string='Monto Total',
                                  compute='_compute_estadisticas',
                                  currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Moneda',
                                  default=lambda self: self.env.company.currency_id)
    
    color = fields.Integer(string='Color')
    
    _sql_constraints = [
        ('codigo_unique', 'unique(codigo)', 'El código del centro de costo debe ser único'),
        ('name_unique', 'unique(name)', 'Ya existe un centro de costo con este nombre')
    ]
    
    @api.model
    def create(self, vals):
        """Convierte el código a mayúsculas automáticamente"""
        if vals.get('codigo'):
            vals['codigo'] = vals['codigo'].upper()
        return super().create(vals)
    
    def write(self, vals):
        """Convierte el código a mayúsculas automáticamente"""
        if vals.get('codigo'):
            vals['codigo'] = vals['codigo'].upper()
        return super().write(vals)
    
    def _compute_estadisticas(self):
        """Calcula estadísticas de uso del centro de costo"""
        for rec in self:
            solicitudes = self.env['ctrl.caja.solicitud'].search([
                ('centro_costo_id', '=', rec.id)
            ])
            rec.cantidad_solicitudes = len(solicitudes)
            rec.monto_total = sum(solicitudes.mapped('monto_estimado'))
    
    def action_view_solicitudes(self):
        """Abre las solicitudes relacionadas con este centro de costo"""
        self.ensure_one()
        return {
            'name': f'Solicitudes - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ctrl.caja.solicitud',
            'view_mode': 'tree,form',
            'domain': [('centro_costo_id', '=', self.id)],
            'context': {'default_centro_costo_id': self.id}
        }