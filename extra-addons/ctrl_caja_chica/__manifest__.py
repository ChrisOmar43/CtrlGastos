{
    "name": "Control de Caja Chica",
    "version": "1.0.3",
    "summary": "Registrar y controlar movimientos de caja chica y arqueos",
    "description": "Módulo para llevar caja chica: movimientos, categorías, arqueos y reportes simples.",
    "author": "ChrisOmar",
    "website": "",
    "category": "Accounting",
    "depends": ["base", "hr", "mail"],
    "data": [
        # Seguridad primero
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        
        # Vistas y datos
        "views/caja_chica_views.xml",        
        "views/arqueo_views.xml",
        "views/solicitud_views.xml",
        "views/autorizador_views.xml",
        "views/tesoreria_views.xml",
        "views/configuracion_views.xml",     
        "views/concepto_views.xml",          
        "views/centro_costo_views.xml",      
        "views/proveedor_views.xml",         
    ],
    "installable": True,
    "application": True,
    "auto_install": False
}