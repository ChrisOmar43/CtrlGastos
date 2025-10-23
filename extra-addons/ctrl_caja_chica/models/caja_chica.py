from odoo import models, fields, api
from odoo.exceptions import ValidationError

class CtrlCajaChica(models.Model):
    _name = 'ctrl.caja.chica'
    _description = 'Movimiento de Caja Chica'
    _order = 'fecha desc, id desc'

    name = fields.Char(string='Referencia', required=False)
    fecha = fields.Date(string='Fecha', default=fields.Date.context_today, required=True)
    tipo = fields.Selection([('entrada','Entrada'),('salida','Salida')], string='Tipo', required=True)
    monto = fields.Monetary(string='Monto', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Moneda', required=True,
                                  default=lambda self: self.env.company.currency_id)
    categoria_id = fields.Many2one('ctrl.caja.param', string='Categoría')
    centro_costo = fields.Char(string='Centro de costo')
    responsable_id = fields.Many2one('hr.employee', string='Responsable')
    proveedor = fields.Many2one('res.partner', string='Proveedor')
    metodo_pago = fields.Selection([('efectivo','Efectivo'),('transferencia','Transferencia'),('cheque','Cheque')], string='Método de pago')
    numero_factura = fields.Char(string='Número de factura')
    estado_pago = fields.Selection([('pendiente','Pendiente'),('pagada','Pagada'),('parcial','Parcial')], string='Estado', default='pendiente')
    observaciones = fields.Text(string='Observaciones')
    arqueo_id = fields.Many2one('ctrl.caja.arqueo', string='Arqueo')
    create_uid = fields.Many2one('res.users', string='Creado por', readonly=True)

    @api.constrains('monto')
    def _check_monto(self):
        for rec in self:
            if rec.monto < 0:
                raise ValidationError('El monto no puede ser negativo.')

    # helper to compute sign for total sum use
    def _sign(self):
        self.ensure_one()
        return 1 if self.tipo == 'entrada' else -1
