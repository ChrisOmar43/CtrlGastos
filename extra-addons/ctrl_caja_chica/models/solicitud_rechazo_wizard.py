from odoo import models, fields, api
from odoo.exceptions import ValidationError

class CtrlCajaSolicitudRechazoWizard(models.TransientModel):
    _name = 'ctrl.caja.solicitud.rechazo.wizard'
    _description = 'Wizard para Rechazar Solicitud'

    solicitud_id = fields.Many2one('ctrl.caja.solicitud', string='Solicitud', required=True)
    nivel = fields.Char(string='Nivel', required=True)
    comentario = fields.Text(string='Motivo del Rechazo', required=True,
                            placeholder='Explique el motivo por el cual rechaza esta solicitud...')

    def action_confirmar_rechazo(self):
        """Confirma el rechazo de la solicitud"""
        self.ensure_one()
        
        if not self.comentario or self.comentario.strip() == '':
            raise ValidationError('Debe especificar un motivo para el rechazo.')
        
        self.solicitud_id.procesar_rechazo(self.nivel, self.comentario)
        
        # Regresar a la vista de autorizaciones según el nivel
        estado_buscar = f'autorizacion_{self.nivel}'
        nivel_num = self.nivel.replace('nivel', '')
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Autorizar Nivel {nivel_num}',
            'res_model': 'ctrl.caja.solicitud',
            'view_mode': 'tree,form',
            'domain': [('estado', '=', estado_buscar)],
            'context': {},
            'target': 'main',
        }