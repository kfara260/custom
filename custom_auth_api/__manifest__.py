{
    'name': 'Custom Authentication API',
    'version': '1.0',
    'summary': 'API for user registration and login',
    'author': 'Karim Ahmed',
    'category': 'Authentication',
    'depends': ['base', 'web', 'hr', 'hr_attendance_zktecho', 'hr_payroll', 'hr_attendance', 'hr_holidays'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        
        'data/email_templates.xml',
        
        'views/hr_employee_views.xml',
        'views/attendance_location_views.xml',
        'views/hr_draft_attendance_view.xml',
        'views/hr_payslip_view.xml',
        'views/hr_leave_type_view.xml',
        'views/res_config_views.xml',
    ],
    'installable': True,
    'application': True,
}
