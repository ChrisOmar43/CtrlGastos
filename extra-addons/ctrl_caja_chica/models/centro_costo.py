from odoo import models, fields, api
from odoo.exceptions import ValidationError

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
    
    # ============ MONTOS POR CENTRO ============
    monto_nivel1 = fields.Monetary(
        string='Monto Nivel 1 (hasta)', 
        required=True, 
        default=1000.0,
        currency_field='currency_id',
        tracking=True,
        help='Solicitudes hasta este monto requieren solo Nivel 1'
    )
    
    monto_nivel2 = fields.Monetary(
        string='Monto Nivel 2 (hasta)', 
        required=True, 
        default=2000.0,
        currency_field='currency_id',
        tracking=True,
        help='Solicitudes hasta este monto requieren Nivel 1 y 2'
    )
    
    # Nivel 3 es automático: mayor a monto_nivel2
    
    # ============ AUTORIZADORES POR NIVEL ============
    autorizador_nivel1_ids = fields.Many2many(
        'res.users',
        'centro_costo_autorizador_nivel1_rel',
        'centro_costo_id',
        'user_id',
        string='Autorizadores Nivel 1',
        domain=[('share', '=', False)],
        help='Usuarios que pueden autorizar solicitudes del Nivel 1 de este centro',
        tracking=True
    )
    
    autorizador_nivel2_ids = fields.Many2many(
        'res.users',
        'centro_costo_autorizador_nivel2_rel',
        'centro_costo_id',
        'user_id',
        string='Autorizadores Nivel 2',
        domain=[('share', '=', False)],
        help='Usuarios que pueden autorizar solicitudes del Nivel 2 de este centro',
        tracking=True
    )
    
    autorizador_nivel3_ids = fields.Many2many(
        'res.users',
        'centro_costo_autorizador_nivel3_rel',
        'centro_costo_id',
        'user_id',
        string='Autorizadores Nivel 3',
        domain=[('share', '=', False)],
        help='Usuarios que pueden autorizar solicitudes del Nivel 3 de este centro',
        tracking=True
    )
    
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
    
    @api.constrains('monto_nivel1', 'monto_nivel2')
    def _check_montos(self):
        """Valida que los montos sean coherentes"""
        for rec in self:
            if rec.monto_nivel1 <= 0:
                raise ValidationError('El monto del Nivel 1 debe ser mayor a cero.')
            if rec.monto_nivel2 <= rec.monto_nivel1:
                raise ValidationError(
                    f'En el centro "{rec.name}": El monto del Nivel 2 (${rec.monto_nivel2:,.2f}) '
                    f'debe ser mayor que el Nivel 1 (${rec.monto_nivel1:,.2f}).'
                )
    
    @api.constrains('autorizador_nivel1_ids', 'autorizador_nivel2_ids', 'autorizador_nivel3_ids')
    def _check_autorizadores(self):
        """Valida que haya al menos un autorizador en nivel 1"""
        for rec in self:
            if rec.activo and not rec.autorizador_nivel1_ids:
                raise ValidationError(
                    f'El centro de costo "{rec.name}" debe tener al menos un autorizador de Nivel 1.'
                )
    @api.constrains('autorizador_nivel1_ids', 'autorizador_nivel2_ids', 'autorizador_nivel3_ids')
    def _check_autorizadores_unicos(self):
        """Evita que un mismo usuario esté en más de un nivel dentro del mismo centro de costo"""
        for rec in self:
            # Reunimos todos los autorizadores
            todos_autorizadores = (
                rec.autorizador_nivel1_ids |
                rec.autorizador_nivel2_ids |
                rec.autorizador_nivel3_ids
            )
            # Verificamos duplicados
            total_usuarios = len(todos_autorizadores)
            usuarios_unicos = len(set(todos_autorizadores.ids))

            if total_usuarios != usuarios_unicos:
                # Encontramos los duplicados para mostrar un mensaje más claro
                duplicados = todos_autorizadores.filtered(
                    lambda u: (
                        u in rec.autorizador_nivel1_ids and u in rec.autorizador_nivel2_ids
                    ) or (
                        u in rec.autorizador_nivel1_ids and u in rec.autorizador_nivel3_ids
                    ) or (
                        u in rec.autorizador_nivel2_ids and u in rec.autorizador_nivel3_ids
                    )
                )

                nombres = ', '.join(duplicados.mapped('name'))
                raise ValidationError(
                    f'El usuario(s) {nombres} está asignado a más de un nivel en el centro de costo "{rec.name}".\n'
                    'Cada usuario solo puede pertenecer a un nivel de autorización por centro.'
                )

    
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
    
    def puede_autorizar(self, user_id, nivel):
        """Verifica si un usuario puede autorizar en este centro de costo para un nivel dado"""
        self.ensure_one()
        if nivel == 'nivel1':
            return user_id in self.autorizador_nivel1_ids.ids
        elif nivel == 'nivel2':
            return user_id in self.autorizador_nivel2_ids.ids
        elif nivel == 'nivel3':
            return user_id in self.autorizador_nivel3_ids.ids
        return False
    
    def get_nivel_requerido(self, monto):
        """Determina qué nivel de autorización requiere un monto EN ESTE CENTRO"""
        self.ensure_one()
        if monto < self.monto_nivel1:
            return 'nivel1'
        elif monto < self.monto_nivel2:
            return 'nivel2'
        else:
            return 'nivel3'
    
    def get_rango_nivel(self, nivel):
        """Retorna el rango de montos para un nivel en formato texto"""
        self.ensure_one()
        if nivel == 'nivel1':
            return f'Nivel 1 (< ${self.monto_nivel1:,.2f})'
        elif nivel == 'nivel2':
            return f'Nivel 2 (${self.monto_nivel1:,.2f} - ${self.monto_nivel2:,.2f})'
        else:
            return f'Nivel 3 (> ${self.monto_nivel2:,.2f})'