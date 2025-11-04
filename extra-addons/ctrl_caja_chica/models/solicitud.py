from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class CtrlCajaSolicitud(models.Model):
    _name = 'ctrl.caja.solicitud'
    _description = 'Solicitud de Compra'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'fecha_solicitud desc, id desc'
    _rec_name = 'numero_solicitud'

    numero_solicitud = fields.Char(string='Número de Solicitud', readonly=True, copy=False)
    fecha_solicitud = fields.Date(string='Fecha de Solicitud', 
                                   default=fields.Date.context_today, 
                                   required=True,
                                   tracking=True)
    
    responsable_id = fields.Many2one('res.users', 
                                     string='Responsable', 
                                     default=lambda self: self.env.user,
                                     readonly=True,
                                     required=True,
                                     tracking=True)
    
    categoria_id = fields.Many2one('ctrl.caja.concepto',
                                   string='Concepto',
                                   domain=[('activo', '=', True)],
                                   tracking=True)
    concepto_otro = fields.Boolean(string='Concepto: Otros', default=False)
    concepto_texto = fields.Char(string='Especificar Concepto')
    
    centro_costo_id = fields.Many2one('ctrl.caja.centro.costo',
                                      string='Centro de Costos',
                                      domain=[('activo', '=', True)],
                                      required=True,
                                      tracking=True)
    
    monto_estimado = fields.Monetary(string='Costo Estimado', 
                                     required=True, 
                                     currency_field='currency_id',
                                     tracking=True)
    currency_id = fields.Many2one('res.currency', 
                                  string='Moneda', 
                                  required=True,
                                  default=lambda self: self.env.company.currency_id)
    
    metodo_pago = fields.Selection([
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('cheque', 'Cheque')
    ], string='Forma de Pago', required=True, tracking=True)
    
    proveedor_id = fields.Many2one('ctrl.caja.proveedor',
                                   string='Proveedor',
                                   domain=[('activo', '=', True)],
                                   tracking=True)
    proveedor_otro = fields.Boolean(string='Proveedor: Otros', default=False)
    proveedor_texto = fields.Char(string='Especificar Proveedor')
    
    estado = fields.Selection([
        ('borrador', 'Borrador'),
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
    
    nivel_requerido = fields.Selection([
        ('nivel1', 'Nivel 1'),
        ('nivel2', 'Nivel 2'),
        ('nivel3', 'Nivel 3')
    ], string='Nivel de Autorización', compute='_compute_nivel_requerido', store=True)
    
    nivel_requerido_texto = fields.Char(
        string='Nivel Requerido',
        compute='_compute_nivel_requerido_texto'
    )
    
    # Campo para determinar si el usuario actual puede autorizar
    puedo_autorizar = fields.Boolean(
        string='Puedo Autorizar',
        compute='_compute_puedo_autorizar',
        search='_search_puedo_autorizar'
    )
    
    # Autorizaciones
    autorizador_nivel1_id = fields.Many2one('res.users', string='Autorizador Nivel 1', readonly=True)
    fecha_autorizacion_nivel1 = fields.Datetime(string='Fecha Autorización N1', readonly=True)
    comentario_nivel1 = fields.Text(string='Comentarios Nivel 1')
    
    autorizador_nivel2_id = fields.Many2one('res.users', string='Autorizador Nivel 2', readonly=True)
    fecha_autorizacion_nivel2 = fields.Datetime(string='Fecha Autorización N2', readonly=True)
    comentario_nivel2 = fields.Text(string='Comentarios Nivel 2')
    
    autorizador_nivel3_id = fields.Many2one('res.users', string='Autorizador Nivel 3', readonly=True)
    fecha_autorizacion_nivel3 = fields.Datetime(string='Fecha Autorización N3', readonly=True)
    comentario_nivel3 = fields.Text(string='Comentarios Nivel 3')
    
    tesorero_id = fields.Many2one('res.users', string='Entregado por', readonly=True)
    fecha_entrega = fields.Datetime(string='Fecha de Entrega', readonly=True)
    comentario_tesoreria = fields.Text(string='Comentarios Tesorería')
    
    descripcion = fields.Text(string='Descripción / Justificación')
    notas_internas = fields.Text(string='Notas Internas')
    movimiento_id = fields.Many2one('ctrl.caja.chica', string='Movimiento de Caja', readonly=True)
    
    @api.depends('monto_estimado', 'centro_costo_id')
    def _compute_nivel_requerido(self):
        """Determina el nivel según el centro de costo"""
        for rec in self:
            if rec.centro_costo_id and rec.monto_estimado:
                rec.nivel_requerido = rec.centro_costo_id.get_nivel_requerido(rec.monto_estimado)
            else:
                rec.nivel_requerido = 'nivel1'
    
    @api.depends('nivel_requerido', 'centro_costo_id')
    def _compute_nivel_requerido_texto(self):
        """Muestra el rango de montos para el nivel según el centro"""
        for rec in self:
            if rec.centro_costo_id and rec.nivel_requerido:
                rec.nivel_requerido_texto = rec.centro_costo_id.get_rango_nivel(rec.nivel_requerido)
            else:
                rec.nivel_requerido_texto = 'Sin definir'
    
    @api.depends('estado', 'centro_costo_id')
    def _compute_puedo_autorizar(self):
        """Determina si el usuario actual puede autorizar esta solicitud"""
        for rec in self:
            rec.puedo_autorizar = False
            
            if not rec.centro_costo_id:
                continue
            
            user_id = self.env.user.id
            
            # Verificar según el estado actual
            if rec.estado == 'autorizacion_nivel1':
                rec.puedo_autorizar = rec.centro_costo_id.puede_autorizar(user_id, 'nivel1')
            elif rec.estado == 'autorizacion_nivel2':
                rec.puedo_autorizar = rec.centro_costo_id.puede_autorizar(user_id, 'nivel2')
            elif rec.estado == 'autorizacion_nivel3':
                rec.puedo_autorizar = rec.centro_costo_id.puede_autorizar(user_id, 'nivel3')
    
    def _search_puedo_autorizar(self, operator, value):
        """Permite buscar solicitudes que el usuario puede autorizar"""
        user_id = self.env.user.id
        
        # Buscar todos los centros donde el usuario es autorizador
        centros = self.env['ctrl.caja.centro.costo'].search([
            '|', '|',
            ('autorizador_nivel1_ids', 'in', [user_id]),
            ('autorizador_nivel2_ids', 'in', [user_id]),
            ('autorizador_nivel3_ids', 'in', [user_id])
        ])
        
        if not centros:
            return [('id', '=', False)]
        
        # Construir dominio complejo
        domain = ['|', '|']
        
        # N1: centros donde soy autorizador N1 Y estado es autorizacion_nivel1
        centros_n1 = centros.filtered(lambda c: user_id in c.autorizador_nivel1_ids.ids)
        if centros_n1:
            domain.append('&')
            domain.append(('centro_costo_id', 'in', centros_n1.ids))
            domain.append(('estado', '=', 'autorizacion_nivel1'))
        else:
            domain.append(('id', '=', False))
        
        # N2: centros donde soy autorizador N2 Y estado es autorizacion_nivel2
        centros_n2 = centros.filtered(lambda c: user_id in c.autorizador_nivel2_ids.ids)
        if centros_n2:
            domain.append('&')
            domain.append(('centro_costo_id', 'in', centros_n2.ids))
            domain.append(('estado', '=', 'autorizacion_nivel2'))
        else:
            domain.append(('id', '=', False))
        
        # N3: centros donde soy autorizador N3 Y estado es autorizacion_nivel3
        centros_n3 = centros.filtered(lambda c: user_id in c.autorizador_nivel3_ids.ids)
        if centros_n3:
            domain.append('&')
            domain.append(('centro_costo_id', 'in', centros_n3.ids))
            domain.append(('estado', '=', 'autorizacion_nivel3'))
        else:
            domain.append(('id', '=', False))
        
        if operator == '=' and value:
            return domain
        else:
            return ['!'] + domain
    
    @api.onchange('concepto_otro')
    def _onchange_concepto_otro(self):
        if self.concepto_otro:
            self.categoria_id = False
        else:
            self.concepto_texto = False
    
    @api.onchange('proveedor_otro')
    def _onchange_proveedor_otro(self):
        if self.proveedor_otro:
            self.proveedor_id = False
        else:
            self.proveedor_texto = False
    
    @api.model
    def create(self, vals):
        if not vals.get('numero_solicitud'):
            vals['numero_solicitud'] = self.env['ir.sequence'].next_by_code('ctrl.caja.solicitud') or 'New'
        return super().create(vals)
    
    def action_solicitar(self):
        """Envía la solicitud para autorización"""
        self.ensure_one()
        
        if not self.categoria_id and not self.concepto_texto:
            raise ValidationError('Debe especificar un concepto.')
        
        if not self.proveedor_id and not self.proveedor_texto:
            raise ValidationError('Debe especificar un proveedor.')
        
        if not self.centro_costo_id:
            raise ValidationError('Debe especificar un centro de costo.')
        
        if self.monto_estimado <= 0:
            raise ValidationError('El costo estimado debe ser mayor a cero.')
        
        if not self.centro_costo_id.autorizador_nivel1_ids:
            raise ValidationError(
                f'El centro de costo "{self.centro_costo_id.name}" no tiene autorizadores configurados. '
                'Por favor contacte al administrador.'
            )
        
        self.estado = 'autorizacion_nivel1'
        
        self.message_post(
            body=f'📋 Solicitud enviada para autorización<br/>'
                 f'Centro de Costo: {self.centro_costo_id.name}<br/>'
                 f'Monto: ${self.monto_estimado:,.2f}<br/>'
                 f'Nivel requerido: {self.nivel_requerido_texto}<br/>'
                 f'Autorizadores disponibles: {", ".join(self.centro_costo_id.autorizador_nivel1_ids.mapped("name"))}',
            message_type='notification'
        )
    
    def _verificar_permiso_autorizacion(self, nivel):
        """Verifica si el usuario actual puede autorizar en este nivel y centro"""
        self.ensure_one()
        
        if not self.centro_costo_id:
            raise UserError('Esta solicitud no tiene un centro de costo asignado.')
        
        puede_autorizar = self.centro_costo_id.puede_autorizar(self.env.user.id, nivel)
        
        if not puede_autorizar:
            autorizadores = getattr(self.centro_costo_id, f'autorizador_{nivel}_ids')
            raise UserError(
                f'No tiene permisos para autorizar solicitudes de {nivel.upper()} '
                f'del centro de costo "{self.centro_costo_id.name}".\n\n'
                f'Autorizadores autorizados: {", ".join(autorizadores.mapped("name"))}'
            )
    
    def action_autorizar_nivel1(self):
        """Autoriza nivel 1"""
        self.ensure_one()
        
        if self.estado != 'autorizacion_nivel1':
            raise UserError('Esta solicitud no está en autorización Nivel 1.')
        
        self._verificar_permiso_autorizacion('nivel1')
        
        self.write({
            'autorizador_nivel1_id': self.env.user.id,
            'fecha_autorizacion_nivel1': fields.Datetime.now(),
        })
        
        if self.nivel_requerido == 'nivel1':
            self.estado = 'autorizado'
            mensaje = f'✅ Solicitud AUTORIZADA por {self.env.user.name} (Nivel 1 - Autorización completa)'
        else:
            self.estado = 'autorizacion_nivel2'
            autorizadores = ", ".join(self.centro_costo_id.autorizador_nivel2_ids.mapped("name"))
            mensaje = f'✅ Autorizado por {self.env.user.name} (Nivel 1)<br/>Pasa a Nivel 2<br/>Autorizadores: {autorizadores}'
        
        self.message_post(body=mensaje, message_type='notification')
        
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
        self.ensure_one()
        if self.estado != 'autorizacion_nivel1':
            raise UserError('Esta solicitud no está en autorización Nivel 1.')
        self._verificar_permiso_autorizacion('nivel1')
        return self._wizard_rechazo('nivel1')
    
    def action_autorizar_nivel2(self):
        """Autoriza nivel 2"""
        self.ensure_one()
        
        if self.estado != 'autorizacion_nivel2':
            raise UserError('Esta solicitud no está en autorización Nivel 2.')
        
        if not self.autorizador_nivel1_id:
            raise UserError('Debe ser autorizada primero por Nivel 1.')
        
        self._verificar_permiso_autorizacion('nivel2')
        
        self.write({
            'autorizador_nivel2_id': self.env.user.id,
            'fecha_autorizacion_nivel2': fields.Datetime.now(),
        })
        
        if self.nivel_requerido == 'nivel2':
            self.estado = 'autorizado'
            mensaje = f'✅ Solicitud AUTORIZADA por {self.env.user.name} (Nivel 2 - Autorización completa)'
        else:
            self.estado = 'autorizacion_nivel3'
            autorizadores = ", ".join(self.centro_costo_id.autorizador_nivel3_ids.mapped("name"))
            mensaje = f'✅ Autorizado por {self.env.user.name} (Nivel 2)<br/>Pasa a Nivel 3<br/>Autorizadores: {autorizadores}'
        
        self.message_post(body=mensaje, message_type='notification')
        
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
        self.ensure_one()
        if self.estado != 'autorizacion_nivel2':
            raise UserError('Esta solicitud no está en autorización Nivel 2.')
        self._verificar_permiso_autorizacion('nivel2')
        return self._wizard_rechazo('nivel2')
    
    def action_autorizar_nivel3(self):
        """Autoriza nivel 3 - autorización final"""
        self.ensure_one()
        
        if self.estado != 'autorizacion_nivel3':
            raise UserError('Esta solicitud no está en autorización Nivel 3.')
        
        if not self.autorizador_nivel1_id or not self.autorizador_nivel2_id:
            raise UserError('Debe ser autorizada primero por Nivel 1 y 2.')
        
        self._verificar_permiso_autorizacion('nivel3')
        
        self.write({
            'autorizador_nivel3_id': self.env.user.id,
            'fecha_autorizacion_nivel3': fields.Datetime.now(),
            'estado': 'autorizado',
        })
        
        self.message_post(
            body=f'✅ Solicitud AUTORIZADA por {self.env.user.name} (Nivel 3 - Autorización completa)',
            message_type='notification'
        )
        
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
        self.ensure_one()
        if self.estado != 'autorizacion_nivel3':
            raise UserError('Esta solicitud no está en autorización Nivel 3.')
        self._verificar_permiso_autorizacion('nivel3')
        return self._wizard_rechazo('nivel3')
    
    def _wizard_rechazo(self, nivel):
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
        self.ensure_one()
        
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
            body=f'❌ Solicitud RECHAZADA por {self.env.user.name} ({nivel.upper()})<br/>Motivo: {comentario}',
            message_type='notification'
        )
    
    def action_cancelar(self):
        self.ensure_one()
        if self.estado in ['autorizado', 'rechazado']:
            raise UserError('No puede cancelar una solicitud autorizada o rechazada.')
        self.estado = 'cancelado'
        self.message_post(body='Solicitud cancelada.', message_type='notification')
    
    def action_volver_borrador(self):
        self.ensure_one()
        if self.estado not in ['rechazado', 'cancelado']:
            raise UserError('Solo puede regresar a borrador solicitudes rechazadas o canceladas.')
        
        self.estado = 'borrador'
        self.autorizador_nivel1_id = False
        self.fecha_autorizacion_nivel1 = False
        self.autorizador_nivel2_id = False
        self.fecha_autorizacion_nivel2 = False
        self.autorizador_nivel3_id = False
        self.fecha_autorizacion_nivel3 = False
        self.comentario_nivel1 = False
        self.comentario_nivel2 = False
        self.comentario_nivel3 = False
        self.message_post(body='Solicitud regresada a borrador.', message_type='notification')
    
    def action_entregar_dinero(self):
        self.ensure_one()
        if self.estado != 'autorizado':
            raise UserError('Solo se puede entregar dinero a solicitudes autorizadas.')
        
        self.write({
            'tesorero_id': self.env.user.id,
            'fecha_entrega': fields.Datetime.now(),
            'estado': 'entregado',
        })
        
        self.message_post(
            body=f'💰 Dinero ENTREGADO por {self.env.user.name}',
            message_type='notification'
        )
        
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
    
    def action_view_movimiento(self):
        self.ensure_one()
        if not self.movimiento_id:
            raise UserError('No hay movimiento de caja asociado.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Movimiento de Caja',
            'res_model': 'ctrl.caja.chica',
            'res_id': self.movimiento_id.id,
            'view_mode': 'form',
            'target': 'current',
        }