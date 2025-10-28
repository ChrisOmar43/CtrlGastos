from odoo import models, fields, api

class CtrlCajaParam(models.Model):
    _name = 'ctrl.caja.param'
    _description = 'Parámetros de Caja Chica'
    _inherit = ['mail.thread', 'mail.activity.mixin'] 
    _order = 'tipo, concepto'

    # Campos principales
    tipo = fields.Selection([
        ('fijo', 'Fijo'),
        ('variable', 'Variable'),
        ('caja_chica', 'Caja Chica')
    ], string='Tipo', required=True, default='caja_chica')
    
    concepto = fields.Char(string='Concepto', required=True, 
                          help='Descripción del concepto de gasto')
    
    centro_costo = fields.Selection([
        ('Alm', 'Almacén'),
        ('Admin', 'Administración'),
        ('Serv', 'Servicio'),
        ('Logis', 'Logística'),
        ('Planta', 'Planta'),
        ('For', 'Foráneo')
    ], string='Centro de Costos')
    
    periodicidad = fields.Selection([
        ('unico', 'Único'),
        ('diario', 'Diario'),
        ('semanal', 'Semanal'),
        ('quincenal', 'Quincenal'),
        ('mensual', 'Mensual'),
        ('bimestral', 'Bimestral'),
        ('trimestral', 'Trimestral'),
        ('semestral', 'Semestral'),
        ('anual', 'Anual')
    ], string='Periodicidad', help='Frecuencia del gasto')
    
    # Campos adicionales útiles
    monto_estimado = fields.Monetary(string='Monto Estimado', 
                                     currency_field='currency_id',
                                     help='Monto promedio o estimado para este concepto')
    currency_id = fields.Many2one('res.currency', string='Moneda', 
                                  default=lambda self: self.env.company.currency_id)
    
    activo = fields.Boolean(string='Activo', default=True)
    notas = fields.Text(string='Notas')
    
    # Campo computado para nombre completo
    name = fields.Char(string='Nombre Completo', compute='_compute_name', store=True)
    
    @api.depends('tipo', 'concepto', 'centro_costo')
    def _compute_name(self):
        """Genera un nombre descriptivo automáticamente"""
        for rec in self:
            parts = []
            if rec.tipo:
                tipo_label = dict(rec._fields['tipo'].selection).get(rec.tipo, '')
                parts.append(f"[{tipo_label}]")
            if rec.concepto:
                parts.append(rec.concepto)
            if rec.centro_costo:
                centro_label = dict(rec._fields['centro_costo'].selection).get(rec.centro_costo, '')
                parts.append(f"({centro_label})")
            
            rec.name = ' '.join(parts) if parts else 'Nuevo Parámetro'
    
    _sql_constraints = [
        ('concepto_unique', 'unique(tipo, concepto, centro_costo)', 
         'Ya existe un parámetro con esta combinación de Tipo, Concepto y Centro de Costo')
    ]
    
    def toggle_active(self):
        """Activa o desactiva el parámetro"""
        for rec in self:
            rec.activo = not rec.activo
    
    def action_view_movimientos(self):
        """Abre vista de movimientos relacionados con este parámetro"""
        self.ensure_one()
        return {
            'name': f'Movimientos - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ctrl.caja.chica',
            'view_mode': 'tree,form',
            'domain': [('categoria_id', '=', self.id)],
            'context': {
                'default_categoria_id': self.id,
                'default_tipo_gasto': self.tipo,
                'default_centro_costo': self.centro_costo,
            }
        }