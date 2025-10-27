{
    "name": "Control de Caja Chica",
    "version": "1.0.1",
    "summary": "Registrar y controlar movimientos de caja chica y arqueos",
    "description": "Módulo para llevar caja chica: movimientos, categorías, arqueos y reportes simples.",
    "author": "ChrisOmar",
    "website": "",
    "category": "Accounting",
    "depends": ["base", "hr"],
    "data": [
        "security/ir.model.access.csv",
        "views/caja_chica_views.xml",
        "views/arqueo_views.xml",
        "views/parametros_views.xml"
    ],
    "installable": True,
    "application": True,
    "auto_install": False
}
