from odoo import models, fields, api
from odoo.exceptions import ValidationError

class CtrlCajaChica(models.Model):
    _name = 'ctrl.caja.chica'
    _description = 'Movimiento de Caja Chica'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # 👈 para chatter y seguimiento
    _order = 'fecha desc, id desc'

    name = fields.Char(string='Referencia', readonly=True, copy=False)

    # Fechas
    fecha_solicitud = fields.Date(string='Fecha Solicitud', help='Cuando el responsable entregó')
    fecha = fields.Date(
        string='Fecha Pago',
        default=fields.Date.context_today,
        required=True,
        help='Cuando se pagó'
    )

    # Campos calculados automáticamente (semana y mes)
    semana = fields.Integer(string='Semana', compute='_compute_fecha_info', store=True)
    mes = fields.Selection([
        ('1', 'Enero'), ('2', 'Febrero'), ('3', 'Marzo'),
        ('4', 'Abril'), ('5', 'Mayo'), ('6', 'Junio'),
        ('7', 'Julio'), ('8', 'Agosto'), ('9', 'Septiembre'),
        ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre')
    ], string='Mes', compute='_compute_fecha_info', store=True)

    # Clasificación del gasto
    tipo_gasto = fields.Selection([
        ('fijo', 'Fijo'),
        ('variable', 'Variable'),
        ('caja_chica', 'Caja Chica')
    ], string='Tipo de Gasto', required=True, default='caja_chica')

    categoria_id = fields.Many2one(
        'ctrl.caja.param',
        string='Concepto',
        domain=[('tipo', '=', 'categoria')]
    )

    centro_costo = fields.Selection([
        ('admin', 'Administración'),
        ('serv', 'Servicio'),
        ('logs', 'Logística'),
        ('planta', 'Planta'),
        ('for', 'Foráneo')
    ], string='Centro de Costos')

    # Monto
    monto = fields.Monetary(string='Desembolso', required=True, currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    # Información de documento
    folio_pago = fields.Char(string='Folio de Pago')
    tipo_documento = fields.Selection([
        ('factura', 'Factura'),
        ('remision', 'Remisión')
    ], string='Tipo Documento')
    numero_factura = fields.Char(string='Número de Factura')

    # Detalle de compra
    cantidad = fields.Float(string='Cantidad', digits=(12, 2))
    unidad = fields.Char(string='Unidad')
    descripcion = fields.Text(string='Descripción')

    # Proveedor y pago
    proveedor = fields.Many2one('res.partner', string='Proveedor')
    estado_pago = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('parcial', 'Parcial')
    ], string='Estatus', default='pagada', tracking=True)

    metodo_pago = fields.Selection([
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('cheque', 'Cheque')
    ], string='Forma de Pago')

    # Relaciones
    responsable_id = fields.Many2one('hr.employee', string='Responsable')
    arqueo_id = fields.Many2one('ctrl.caja.arqueo', string='Arqueo')

    # Auditoría
    create_uid = fields.Many2one('res.users', string='Creado por', readonly=True)

    # ==== MÉTODOS ====

    @api.depends('fecha')
    def _compute_fecha_info(self):
        """Calcula automáticamente semana y mes desde la fecha de pago."""
        for rec in self:
            if rec.fecha:
                rec.semana = rec.fecha.isocalendar()[1]
                rec.mes = str(rec.fecha.month)
            else:
                rec.semana = 0
                rec.mes = False

    @api.constrains('monto')
    def _check_monto(self):
        for rec in self:
            if rec.monto < 0:
                raise ValidationError('El monto no puede ser negativo.')

    @api.model
    def create(self, vals):
        """Genera secuencia automática para la referencia."""
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('ctrl.caja.chica') or 'New'
        return super().create(vals)

    def _sign(self):
        """Helper para cálculos — todos los movimientos son salidas por defecto."""
        self.ensure_one()
        return -1
