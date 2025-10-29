from odoo import models, fields, api, exceptions
from odoo.exceptions import ValidationError, UserError

class CtrlCajaSolicitud(models.Model):
    _name = 'ctrl.caja.solicitud'
    _description = 'Solicitud de Compra'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'fecha_solicitud desc, id desc'
    _rec_name = 'numero_solicitud'

    # Información básica
    numero_solicitud = fields.Char(string='Número de Solicitud', readonly=True, copy=False)
    fecha_solicitud = fields.Date(string='Fecha de Solicitud', 
                                   default=fields.Date.context_today, 
                                   required=True,
                                   tracking=True)
    
    # Solicitante (se llena automáticamente con el usuario actual)
    responsable_id = fields.Many2one('res.users', 
                                     string='Responsable', 
                                     default=lambda self: self.env.user,
                                     readonly=True,
                                     required=True,
                                     tracking=True)
    
    # Concepto con opción "Otros"
    categoria_id = fields.Many2one('ctrl.caja.param', 
                                   string='Concepto',
                                   domain=[('activo', '=', True)])
    concepto_otro = fields.Boolean(string='Concepto: Otros', default=False)
    concepto_texto = fields.Char(string='Especificar Concepto', 
                                 invisible="not concepto_otro")
    
    # Centro de Costos
    centro_costo = fields.Selection([
        ('alm', 'Almacén'),
        ('admin', 'Administración'),
        ('serv', 'Servicio'),
        ('logis', 'Logística'),
        ('planta', 'Planta'),
        ('for', 'Foráneo')
    ], string='Centro de Costos', tracking=True)
    
    # Monto
    monto_estimado = fields.Monetary(string='Costo Estimado', 
                                     required=True, 
                                     currency_field='currency_id',
                                     tracking=True)
    currency_id = fields.Many2one('res.currency', 
                                  string='Moneda', 
                                  required=True,
                                  default=lambda self: self.env.company.currency_id)
    
    # Forma de pago
    metodo_pago = fields.Selection([
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('cheque', 'Cheque')
    ], string='Forma de Pago', required=True, tracking=True)
    
    # Proveedor con opción "Otros"
    proveedor_id = fields.Many2one('res.partner', string='Proveedor')
    proveedor_otro = fields.Boolean(string='Proveedor: Otros', default=False)
    proveedor_texto = fields.Char(string='Especificar Proveedor',
                                  invisible="not proveedor_otro")
    
    # Estado de la solicitud
    estado = fields.Selection([
        ('borrador', 'Borrador'),
        ('solicitado', 'Solicitado'),
        ('autorizacion_nivel1', 'En Autorización Nivel 1'),
        ('autorizacion_nivel2', 'En Autorización Nivel 2'),
        ('autorizacion_nivel3', 'En Autorización Nivel 3'),
        ('autorizado', 'Autorizado'),
        ('entregado', 'Entregado'),
        ('rechazado', 'Rechazado'),
        ('cancelado', 'Cancelado')
    ], string='Estatus', 
       default='borrador', 
       required=True, 
       tracking=True,
       readonly=True)
    
    # Niveles de autorización
    nivel_requerido = fields.Selection([
        ('nivel1', 'Nivel 1 (< $1,000)'),
        ('nivel2', 'Nivel 2 ($1,000 - $2,000)'),
        ('nivel3', 'Nivel 3 (> $2,000)')
    ], string='Nivel de Autorización', compute='_compute_nivel_requerido', store=True)
    
    # Campos de autorización
    autorizador_nivel1_id = fields.Many2one('res.users', string='Autorizador Nivel 1', readonly=True)
    fecha_autorizacion_nivel1 = fields.Datetime(string='Fecha Autorización N1', readonly=True)
    comentario_nivel1 = fields.Text(string='Comentarios Nivel 1')
    
    autorizador_nivel2_id = fields.Many2one('res.users', string='Autorizador Nivel 2', readonly=True)
    fecha_autorizacion_nivel2 = fields.Datetime(string='Fecha Autorización N2', readonly=True)
    comentario_nivel2 = fields.Text(string='Comentarios Nivel 2')
    
    autorizador_nivel3_id = fields.Many2one('res.users', string='Autorizador Nivel 3', readonly=True)
    fecha_autorizacion_nivel3 = fields.Datetime(string='Fecha Autorización N3', readonly=True)
    comentario_nivel3 = fields.Text(string='Comentarios Nivel 3')
    
    # Campos de Tesorería
    tesorero_id = fields.Many2one('res.users', string='Entregado por', readonly=True)
    fecha_entrega = fields.Datetime(string='Fecha de Entrega', readonly=True)
    comentario_tesoreria = fields.Text(string='Comentarios Tesorería')
    
    # Información adicional
    descripcion = fields.Text(string='Descripción / Justificación')
    notas_internas = fields.Text(string='Notas Internas')
    
    # Relación con movimiento de caja (una vez autorizado y pagado)
    movimiento_id = fields.Many2one('ctrl.caja.chica', string='Movimiento de Caja', readonly=True)
    
    @api.depends('monto_estimado')
    def _compute_nivel_requerido(self):
        """Determina el nivel de autorización según el monto"""
        for rec in self:
            if rec.monto_estimado < 1000:
                rec.nivel_requerido = 'nivel1'
            elif rec.monto_estimado < 2000:
                rec.nivel_requerido = 'nivel2'
            else:
                rec.nivel_requerido = 'nivel3'
    
    @api.onchange('concepto_otro')
    def _onchange_concepto_otro(self):
        """Limpia el concepto cuando se activa/desactiva 'Otros'"""
        if self.concepto_otro:
            self.categoria_id = False
        else:
            self.concepto_texto = False
    
    @api.onchange('proveedor_otro')
    def _onchange_proveedor_otro(self):
        """Limpia el proveedor cuando se activa/desactiva 'Otros'"""
        if self.proveedor_otro:
            self.proveedor_id = False
        else:
            self.proveedor_texto = False
    
    @api.model
    def create(self, vals):
        """Genera número de solicitud automáticamente"""
        if not vals.get('numero_solicitud'):
            vals['numero_solicitud'] = self.env['ir.sequence'].next_by_code('ctrl.caja.solicitud') or 'New'
        return super().create(vals)
    
    def action_solicitar(self):
        """Envía la solicitud para autorización"""
        self.ensure_one()
        
        # Validaciones
        if not self.categoria_id and not self.concepto_texto:
            raise ValidationError('Debe especificar un concepto.')
        
        if not self.proveedor_id and not self.proveedor_texto:
            raise ValidationError('Debe especificar un proveedor.')
        
        if self.monto_estimado <= 0:
            raise ValidationError('El costo estimado debe ser mayor a cero.')
        
        # Cambiar estado según nivel requerido
        if self.nivel_requerido == 'nivel1':
            self.estado = 'autorizacion_nivel1'
        elif self.nivel_requerido == 'nivel2':
            self.estado = 'autorizacion_nivel1'  # Empieza por nivel 1
        else:  # nivel3
            self.estado = 'autorizacion_nivel1'  # Empieza por nivel 1
        
        self.message_post(
            body=f'Solicitud enviada para autorización (Nivel requerido: {self.nivel_requerido})',
            message_type='notification'
        )
    
    def action_cancelar(self):
        """Cancela la solicitud"""
        self.ensure_one()
        if self.estado in ['autorizado', 'rechazado']:
            raise UserError('No puede cancelar una solicitud autorizada o rechazada.')
        
        self.estado = 'cancelado'
        self.message_post(body='Solicitud cancelada por el usuario.', message_type='notification')
    
    def action_volver_borrador(self):
        """Regresa la solicitud a borrador"""
        self.ensure_one()
        if self.estado not in ['rechazado', 'cancelado']:
            raise UserError('Solo puede regresar a borrador solicitudes rechazadas o canceladas.')
        
        self.estado = 'borrador'
        # Limpiar autorizaciones
        self.autorizador_nivel1_id = False
        self.fecha_autorizacion_nivel1 = False
        self.autorizador_nivel2_id = False
        self.fecha_autorizacion_nivel2 = False
        self.autorizador_nivel3_id = False
        self.fecha_autorizacion_nivel3 = False
    
    @api.constrains('monto_estimado')
    def _check_monto(self):
        for rec in self:
            if rec.monto_estimado < 0:
                raise ValidationError('El monto no puede ser negativo.')
    
    def action_view_movimiento(self):
        """Abre el movimiento de caja relacionado"""
        self.ensure_one()
        if not self.movimiento_id:
            return False
        
        return {
            'name': 'Movimiento de Caja',
            'type': 'ir.actions.act_window',
            'res_model': 'ctrl.caja.chica',
            'view_mode': 'form',
            'res_id': self.movimiento_id.id,
            'target': 'current',
        }
    
    def action_crear_solicitud(self):
        """Abre el formulario para crear una nueva solicitud"""
        return {
            'name': 'Nueva Solicitud',
            'type': 'ir.actions.act_window',
            'res_model': 'ctrl.caja.solicitud',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_responsable_id': self.env.user.id,
            }
        }
    
    # ==================== MÉTODOS DE AUTORIZACIÓN ====================
    
    def action_autorizar_nivel1(self):
        """Autoriza la solicitud en Nivel 1"""
        self.ensure_one()
        
        if self.estado != 'autorizacion_nivel1':
            raise UserError('Esta solicitud no está en estado de autorización Nivel 1.')
        
        # Registrar autorización
        self.write({
            'autorizador_nivel1_id': self.env.user.id,
            'fecha_autorizacion_nivel1': fields.Datetime.now(),
        })
        
        # Determinar siguiente estado según el nivel requerido
        if self.nivel_requerido == 'nivel1':
            # Solo necesita nivel 1, queda autorizado
            self.estado = 'autorizado'
            self.message_post(body='✅ Solicitud AUTORIZADA por Nivel 1 (autorización completa)', 
                            message_type='notification')
        else:
            # Necesita más niveles, pasa al siguiente
            self.estado = 'autorizacion_nivel2'
            self.message_post(body='✅ Autorizado por Nivel 1. Pasa a autorización Nivel 2.', 
                            message_type='notification')
        
        # Recargar la vista actual
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Autorizado',
                'message': 'Solicitud autorizada exitosamente',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
    
    def action_rechazar_nivel1(self):
        """Rechaza la solicitud en Nivel 1"""
        self.ensure_one()
        
        if self.estado != 'autorizacion_nivel1':
            raise UserError('Esta solicitud no está en estado de autorización Nivel 1.')
        
        return self._wizard_rechazo('nivel1')
    
    def action_autorizar_nivel2(self):
        """Autoriza la solicitud en Nivel 2"""
        self.ensure_one()
        
        if self.estado != 'autorizacion_nivel2':
            raise UserError('Esta solicitud no está en estado de autorización Nivel 2.')
        
        if not self.autorizador_nivel1_id:
            raise UserError('Esta solicitud debe ser autorizada primero por Nivel 1.')
        
        # Registrar autorización
        self.write({
            'autorizador_nivel2_id': self.env.user.id,
            'fecha_autorizacion_nivel2': fields.Datetime.now(),
        })
        
        # Determinar siguiente estado según el nivel requerido
        if self.nivel_requerido == 'nivel2':
            # Solo necesita hasta nivel 2, queda autorizado
            self.estado = 'autorizado'
            self.message_post(body='✅ Solicitud AUTORIZADA por Nivel 2 (autorización completa)', 
                            message_type='notification')
        else:
            # Necesita nivel 3, pasa al siguiente
            self.estado = 'autorizacion_nivel3'
            self.message_post(body='✅ Autorizado por Nivel 2. Pasa a autorización Nivel 3.', 
                            message_type='notification')
        
        # Recargar la vista actual
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Autorizado',
                'message': 'Solicitud autorizada exitosamente',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
    
    def action_rechazar_nivel2(self):
        """Rechaza la solicitud en Nivel 2"""
        self.ensure_one()
        
        if self.estado != 'autorizacion_nivel2':
            raise UserError('Esta solicitud no está en estado de autorización Nivel 2.')
        
        return self._wizard_rechazo('nivel2')
    
    def action_autorizar_nivel3(self):
        """Autoriza la solicitud en Nivel 3 (autorización final)"""
        self.ensure_one()
        
        if self.estado != 'autorizacion_nivel3':
            raise UserError('Esta solicitud no está en estado de autorización Nivel 3.')
        
        if not self.autorizador_nivel1_id or not self.autorizador_nivel2_id:
            raise UserError('Esta solicitud debe ser autorizada primero por Nivel 1 y Nivel 2.')
        
        # Registrar autorización final
        self.write({
            'autorizador_nivel3_id': self.env.user.id,
            'fecha_autorizacion_nivel3': fields.Datetime.now(),
            'estado': 'autorizado',
        })
        
        self.message_post(body='✅ Solicitud AUTORIZADA por Nivel 3 (autorización completa)', 
                        message_type='notification')
        
        # Recargar la vista actual
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Autorizado',
                'message': 'Solicitud autorizada exitosamente',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
    
    def action_rechazar_nivel3(self):
        """Rechaza la solicitud en Nivel 3"""
        self.ensure_one()
        
        if self.estado != 'autorizacion_nivel3':
            raise UserError('Esta solicitud no está en estado de autorización Nivel 3.')
        
        return self._wizard_rechazo('nivel3')
    
    def _wizard_rechazo(self, nivel):
        """Abre wizard para agregar comentario de rechazo"""
        return {
            'name': 'Motivo de Rechazo',
            'type': 'ir.actions.act_window',
            'res_model': 'ctrl.caja.solicitud.rechazo.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_solicitud_id': self.id,
                'default_nivel': nivel,
            }
        }
    
    def procesar_rechazo(self, nivel, comentario):
        """Procesa el rechazo de una solicitud"""
        self.ensure_one()
        
        # Registrar quien rechazó y cuándo
        if nivel == 'nivel1':
            self.write({
                'autorizador_nivel1_id': self.env.user.id,
                'fecha_autorizacion_nivel1': fields.Datetime.now(),
                'comentario_nivel1': comentario,
            })
        elif nivel == 'nivel2':
            self.write({
                'autorizador_nivel2_id': self.env.user.id,
                'fecha_autorizacion_nivel2': fields.Datetime.now(),
                'comentario_nivel2': comentario,
            })
        elif nivel == 'nivel3':
            self.write({
                'autorizador_nivel3_id': self.env.user.id,
                'fecha_autorizacion_nivel3': fields.Datetime.now(),
                'comentario_nivel3': comentario,
            })
        
        self.estado = 'rechazado'
        self.message_post(
            body=f'❌ Solicitud RECHAZADA por {nivel.upper()}<br/>Motivo: {comentario}',
            message_type='notification'
        )
    
    # ==================== MÉTODOS DE TESORERÍA ====================
    
    def action_entregar_dinero(self):
        """Registra la entrega de dinero al solicitante"""
        self.ensure_one()
        
        if self.estado != 'autorizado':
            raise UserError('Solo se puede entregar dinero a solicitudes autorizadas.')
        
        # Registrar entrega
        self.write({
            'tesorero_id': self.env.user.id,
            'fecha_entrega': fields.Datetime.now(),
            'estado': 'entregado',
        })
        
        self.message_post(
            body=f'💰 Dinero ENTREGADO al solicitante por {self.env.user.name}',
            message_type='notification'
        )
        
        # Cerrar y mostrar notificación
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '💰 Entregado',
                'message': 'Dinero entregado exitosamente',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }