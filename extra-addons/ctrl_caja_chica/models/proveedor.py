from odoo import models, fields, api

class CtrlCajaProveedor(models.Model):
    _name = 'ctrl.caja.proveedor'
    _description = 'Proveedores de Caja Chica'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Nombre del Proveedor', required=True, tracking=True)
    
    codigo = fields.Char(string='Código/RFC', tracking=True,
                        help='RFC o código del proveedor')
    
    telefono = fields.Char(string='Teléfono', tracking=True)
    
    email = fields.Char(string='Email', tracking=True)
    
    direccion = fields.Text(string='Dirección')
    
    contacto = fields.Char(string='Persona de Contacto', tracking=True)
    
    notas = fields.Text(string='Notas')
    
    activo = fields.Boolean(string='Activo', default=True, tracking=True)
    
    # Estadísticas
    cantidad_solicitudes = fields.Integer(string='# Solicitudes',
                                         compute='_compute_estadisticas')
    monto_total = fields.Monetary(string='Monto Total Comprado',
                                  compute='_compute_estadisticas',
                                  currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Moneda',
                                  default=lambda self: self.env.company.currency_id)
    
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Ya existe un proveedor con este nombre')
    ]
    
    def _compute_estadisticas(self):
        """Calcula estadísticas de compras al proveedor"""
        for rec in self:
            solicitudes = self.env['ctrl.caja.solicitud'].search([
                ('proveedor_id', '=', rec.id)
            ])
            rec.cantidad_solicitudes = len(solicitudes)
            rec.monto_total = sum(solicitudes.mapped('monto_estimado'))
    
    def action_view_solicitudes(self):
        """Abre las solicitudes relacionadas con este proveedor"""
        self.ensure_one()
        return {
            'name': f'Compras a {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ctrl.caja.solicitud',
            'view_mode': 'tree,form',
            'domain': [('proveedor_id', '=', self.id)],
            'context': {'default_proveedor_id': self.id}
        }