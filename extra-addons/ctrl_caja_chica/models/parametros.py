from odoo import models, fields

class CtrlCajaParam(models.Model):
    _name = 'ctrl.caja.param'
    _description = 'Parámetros de Caja (categorías / centros de costo)'

    name = fields.Char(string='Nombre', required=True)
    tipo = fields.Selection([('categoria','Categoría'),('centro','Centro de costo')], string='Tipo', default='categoria')
    descripcion = fields.Text(string='Descripción')
