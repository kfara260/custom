from odoo import http
from odoo.http import request,Controller, route, content_disposition
import json
from odoo import models, fields, api
from datetime import datetime, timedelta
import base64
from pytz import timezone, utc
import pytz
import hashlib 
# from odoo.http import request, Controller, route, content_disposition
from werkzeug.wrappers import Response
import base64 


def attachment_list_def(att_id):
    attachments = request.env['ir.attachment'].sudo().search([ 
        ('res_model', '=', 'hr.leave'),
        ('res_id', '=', att_id)
    ])
    attachment_list = []
    for att in attachments:
        attachment_list.append({
            "id": att.id,
            "name": att.name,
            "mimetype": att.mimetype,
            "url": f"/public/attachment/{att.id}"
        })
    return attachment_list
        
class AuthController(http.Controller):


    @http.route('/api/login', type='json', auth="public", methods=['POST'], csrf=False)
    def login(self):
        data = json.loads(request.httprequest.data.decode())
        identifier = data.get("email")  
        password = data.get("password")
        db_name = request.db or data.get('db') or request.session.db
        mac_address = data.get("mac_address")

        if not identifier or not password:
            return {"status": "error", 'db_name': db_name, "message": "The Field email, password, token is Requierd"}

        try:
            # hashed_password = hashlib.sha256(password.encode()).hexdigest()

            # Check if the user exists in the system
            user = request.env['hr.employee'].sudo().search(
                ['&', ('password', '=', password), '|', ('work_email', '=', identifier), ('code_num', '=', identifier)],
                limit=1)
            
            if not user: 
                return {"status": "error", "message": "Failed. Please check your email/code number or password."}

            if user.mac_address != mac_address:
                return {"status": "error", "message": "Failed. should login from same mac address."}

            return {"status": "success", 
                    "message": "Login successful", 
                    "id": user.id,
                    "is_admin": user.is_admin, 
                }
        except Exception as error:
            return {"status": "error", "message": f"An error occurred during login: {str(error)}"}





    @http.route('/api/logout', type='json', auth="public", methods=['POST'], csrf=False)
    def logout(self):
        data = json.loads(request.httprequest.data.decode())
        code_num = data.get("code_num")
        mac_address = data.get("mac_address")

        try:
            # Check if the employee exists
            employee = request.env['hr.employee'].sudo().search([('code_num', '=', code_num)], limit=1)
            if not employee:
                return { 'status': 400,  'message': 'The code number does not exist'}
            
            if employee.mac_address != mac_address:
                return {"status": "error", "message": "Failed. Failed. should logout from same mac address."}
        except Exception as error:
            return {"status": "error", "message": f"An error occurred during logout: {str(error)}"}




    @http.route('/api/update-token', type='json', auth="public", methods=['POST'], csrf=False)
    def updateToken(self):
        data = json.loads(request.httprequest.data.decode())
        token = data.get("token")

        if not token:
            return {"status": "error", "message": "The Field token is Required"}

        try:
            return {"status": "success", "message": "Token successful", "token": token}
        except Exception as error:
            return {"status": "error", "message": "Failed Process. Please try again."}





    @http.route('/api/check-code', type='json', auth='public', methods=['POST'], csrf=False)
    def checkCode(self): 
        try:
            data = json.loads(request.httprequest.data.decode())
            code_num = data.get("code_num")

            # Validate required fields
            if not code_num:
                return {'status': 400, 'message': "The field 'code_num' is required."}

            # Check if the employee exists
            employee = request.env['hr.employee'].sudo().search([('code_num', '=', code_num)], limit=1)
            if not employee:
                return { 'status': 400,  'message': 'The code number does not exist'}
            
            # Check if employee has a work email (used to determine login-ready or verification)
            if employee.work_email and employee.password:
                return {'status': 200, 'message': 'Login page', 'result': True}
            else:
                return {'status': 200, 'message': 'Verification page', 'result': False}
            
        except Exception as error:
            return {'status': 500, 'message': "An error occurred during check code", 'error': str(error)}









    @http.route('/api/verification/email', type='json', auth='public', methods=['POST'], csrf=False)
    def verificationEmail(self):
        try:
            data = json.loads(request.httprequest.data.decode())
            email = data.get('email')

            # Validate required fields
            if not email:
                return {'status': 400, 'message': "The field email required"}

            # Check if the partner exists
            employee = request.env['hr.employee'].sudo().search([('work_email', '=', email)], limit=1)
            if not employee:
                return {
                    'status': 400, 
                    'message': 'this email not exist', 
                }
                
            # Generate a otp number
            otp = employee.sudo().generate_otp_number()
            
            # Send email to employee
            template = request.env.ref('custom_auth_api.email_template_otp_number_employee')
            if template:
                template.sudo().send_mail(employee.id, force_send=True)

            return {
                'status': 200,
                'username': employee.name,
                'email': employee.work_email,
                'otp': otp,
                'message': "otp send to your email",
            }
        
        except Exception as error:
            return {'status': 500, 'message': "An error occurred during verification email", 'error': str(error)}










    @http.route('/api/verification/manager-email', type='json', auth='public', methods=['POST'], csrf=False)
    def verificationManagerEmail(self):
        try:
            data = json.loads(request.httprequest.data.decode())
            code_num = data.get("code_num")

            # Validate required fields
            if not code_num:
                return {'status': 400, 'message': "The field code_num required"}

            # Check if the partner exists
            employee = request.env['hr.employee'].sudo().search([('code_num', '=', code_num)], limit=1)
            if not employee:
                return {
                    'status': 400, 
                    'message': 'this employee not exist', 
                }

            # Get manager's email
            manager_email = employee.parent_id.work_email if employee.parent_id else None
            if not manager_email:
                return {'status': 400, 'message': "Manager email not found"}

            # Send email to manager
            template = request.env.ref('custom_auth_api.email_template_otp_number_manager')
            if template:
                template.sudo().send_mail(employee.id, force_send=True)

            # Create a mail.activity for the manager
            # activity = request.env['mail.activity'].sudo().create({
            #     'activity_type_id': request.env.ref('mail.mail_activity_data_todo').id,
            #     'res_model': 'hr.employee',
            #     'res_id': employee.id,
            #     'user_id': employee.parent_id.parent_user_id.id,
            #     'summary': f'Verify the request for {employee.name}',
            #     'note': f'Please verify the request made by {employee.name}.',
            #     'date_deadline': fields.Date.today(),  
            # })
            if employee.parent_id.user_id:
                employee.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary='Verification Request',
                    note=f'A verification request has been initiated for <b>{employee.name}</b>.',
                    user_id=employee.parent_id.user_id.id,
                )

            
            return {
                'status': 200, 
                'username': employee.name,
                'email': employee.work_email,
                # 'activity': activity, 
                'message': "A request done has been sent to the manager",
            }
        
        except Exception as error:
            return {'status': 500, 'message': "An error occurred during verification email", 'error': str(error)}








    @http.route('/api/verification/manager/otp', type='json', auth='public', methods=['POST'], csrf=False)
    def verificationManagerOtp(self): 
        try:
            data = json.loads(request.httprequest.data.decode())
            code_num = data.get("code_num")
            otp_num = data.get('otp_num')

            # Validate required fields
            if not otp_num or not code_num:
                return {'status': 400, 'message': "The field otp_num, code_num required"}

            # Check if the partner exists
            employee = request.env['hr.employee'].sudo().search([('code_num', '=', code_num)], limit=1)
            if not employee:
                return {
                    'status': 400, 
                    'message': 'this Code Number not exist', 
                }
                
            # Check if the provided otp number matches
            if employee.otp_number != otp_num:
                return {'status': 400, 'message': 'Invalid otp or The otp has expired or changed'}

            # Check expiration (assuming expiration is in hours)
            expiration_hours = int(request.env['ir.config_parameter'].sudo().get_param(
                'custom_auth_api.expiration_hours', default=1
            ))
            expiration_time = employee.generated_at + timedelta(hours=expiration_hours)
            if fields.Datetime.now() > expiration_time:
                return {'status': 400, 'message': 'The otp has expired or changed, please enter the new otp'}

            return {
                'status': 200,
                'message': "successfully active",
            }
        
        except Exception as error:
            return {'status': 500, 'message': "An error occurred during verification email", 'error': str(error)}







    @http.route('/api/verification/otp', type='json', auth='public', methods=['POST'], csrf=False)
    def verificationOtp(self): 
        try:
            data = json.loads(request.httprequest.data.decode())
            email = data.get('email')
            otp_num = data.get('otp_num')

            # Validate required fields
            if not otp_num or not email:
                return {'status': 400, 'message': "The field otp_num, email required"}

            # Check if the partner exists
            employee = request.env['hr.employee'].sudo().search([('work_email', '=', email)], limit=1)
            if not employee:
                return {
                    'status': 400, 
                    'message': 'this email not exist', 
                }
                
            # Check if the provided otp number matches
            if employee.otp_number != otp_num:
                return {'status': 400, 'message': 'Invalid otp or The otp has expired or changed'}

            # Check expiration (assuming expiration is in hours)
            expiration_hours = int(request.env['ir.config_parameter'].sudo().get_param(
                'custom_auth_api.expiration_hours', default=1
            ))
            expiration_time = employee.generated_at + timedelta(hours=expiration_hours)
            if fields.Datetime.now() > expiration_time:
                return {'status': 400, 'message': 'The otp has expired or changed, please enter the new otp'}

            return {
                'status': 200,
                'message': "successfully active",
            }
        
        except Exception as error:
            return {'status': 500, 'message': "An error occurred during verification email", 'error': str(error)}








    @http.route('/api/register', type='json', auth='public', methods=['POST'], csrf=False)
    def register(self):
        try:
            data = json.loads(request.httprequest.data.decode())
            code_num = data.get("code_num")
            password = data.get("password")
            confirm_password = data.get("confirm_password")
            mac_address = data.get("mac_address")
            

            # Validate required fields
            if not code_num or not password or not confirm_password or not mac_address:
                return {'status': 400, 'message': "The fields code_num, password, confirm password and mac address are required"}

            # Check if passwords match
            if password != confirm_password:
                return {'status': 400, 'message': "Password and Confirm Password do not match"}
            
            # Check if a user with the same email already exists
            existing_user = request.env['hr.employee'].sudo().search([('code_num', '=', code_num)], limit=1)
            if not existing_user:
                return {'status': 400, 'message': "A user Not exists"}

            if existing_user.mac_address:
                return {'status': 400, 'message': "This user already have mac Address"}
            
            # Create the new user
            existing_user.sudo().write({
                'password': password,
                'mac_address': mac_address,
            })

            return {
                'status': 200,
                'message': "successfully User registered.",
            }
        
        except Exception as error:
            return {'status': 500, 'message': "An error occurred during registration", 'error': str(error)}









    @http.route('/api/reset-password', type='json', auth='public', methods=['POST'], csrf=False)
    def resetPassword(self):
        try:
            data = json.loads(request.httprequest.data.decode())
            identifier = data.get("email")  
            password = data.get("password")
            confirm_password = data.get("confirm_password")

            # Validate required fields
            if not password or not identifier or not confirm_password:
                return {'status': 400, 'message': "The fields email, password and or not confirm_password are required"}

            # Check if passwords match
            if password != confirm_password:
                return {'status': 400, 'message': "Password and Confirm Password do not match"}

            # Check if a user with the same email already exists
            existing_user = request.env['hr.employee'].sudo().search(
                ['&', ('password', '=', password), '|', ('work_email', '=', identifier), ('code_num', '=', identifier)],
                limit=1)

            if not existing_user:
                return {'status': 400, 'message': "A user with this email not exists"}

            # Create the new user
            existing_user.sudo().write({
                'password': password,
            })

            return {
                'status': 200,
                'message': "Password reset successfully",
                'user': {
                    'name': existing_user.name,
                    'email': existing_user.work_email,
                    'id': existing_user.id
                }
            }
        
        except Exception as error:
            return {'status': 500, 'message': "An error occurred during registration", 'error': str(error)}









    @http.route('/api/attendance-location', type='json', auth='public', methods=['POST'], csrf=False)
    def get_employee_location(self):
        try:
            data = json.loads(request.httprequest.data.decode())
            employee_id = data.get('employee_id')
            
            if not employee_id:
                return {"status":"error", "message": "Invalid or missing employee_id. Ensure it's a valid number."}

            # Search for employee record
            employee = request.env['hr.employee'].sudo().search([('id', '=', int(employee_id))], limit=1)
            
            if not employee:
                return {'status': 'error', 'message': 'Employee not found'}

            # Check for check-in/check-out locations
            if not employee.location_ids:
                return {'status': 'failed', 'message': 'Employee does not have location'}

            # Prepare the response data
            employee_data = {
                'id': employee.id,
                'name': employee.name,
                'locations': [
                    {
                        'latitude': loc.latitude,
                        'longitude': loc.longitude,
                        'accepted_radius': loc.accepted_radius,
                    }
                    for loc in employee.location_ids
                ] if employee.location_ids else None,
            }

            return {'status': 'success', 'data': employee_data}

        except Exception as error:
            return {
                'status': 500,
                'message': 'An error occurred while fetching attendance location',
                'error': str(error)
            }







    @http.route('/api/attendance/checkin-checkout', type='json', auth='public', methods=['POST'], csrf=False)
    def checkin_checkout(self): 
        try:
            data = json.loads(request.httprequest.data.decode())
            employee_id = data.get('employee_id')
            date_time = data.get('date_time')
            date = data.get('date')
            attendance_status = data.get('attendance_status')
            location_status = data.get('location_status')

            if not employee_id or not date_time or not date or not attendance_status :
                return {"message": "Missing employee_id or check_in or date_time or date or attendance_status"}

            # Get the employee record
            employee = request.env['hr.employee'].sudo().browse(employee_id)

            if not employee:
                return {"message": "Invalid employee_id"}

            # Parse check_in
            try:
                local_tz = pytz.timezone("Africa/Cairo")  # Replace with your local timezone

                # Convert local time to UTC
                local_dt = local_tz.localize(datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S"))
                date_time_utc = local_dt.astimezone(pytz.utc).replace(tzinfo=None)  # convert to naive UTC

            except Exception as e:
                return {"message": f"Invalid date_time format: {str(e)}"}

            # Check if there's already a check-in for the same employee on the same day
            # existing_attendance = request.env['hr.draft.attendance'].sudo().search([
            #     ('employee_id', '=', employee.id),
            #     ('date', '=', date),
            #     ('attendance_status', '=', attendance_status),
            # ], limit=1)
            existing_attendance = request.env['hr.draft.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
                ('name', '=', date_time_utc),
            ], limit=1)

            if existing_attendance:
                return {"message": "Employee has already checked in for today."}


            res = request.env['hr.draft.attendance'].sudo().create({
                'employee_id': employee.id,
                'name': date_time_utc,
                'date': date,
                'attendance_status': attendance_status,
                'location_status': location_status
            })
            # Get user's timezone or default to Cairo
            tz_name = request.env.context.get('tz') or 'Africa/Cairo'
            user_tz = pytz.timezone(tz_name)

            # Parse datetime in UTC and convert to user time zone
            utc_dt = fields.Datetime.from_string(res.name)
            localized_dt = pytz.UTC.localize(utc_dt).astimezone(user_tz)

            
            return {
                "success": True,
                "datetime": localized_dt.strftime('%Y-%m-%d %H:%M:%S'),
                "message": "check in successfully" if attendance_status == 'sign_in' else "check out successfully"
            }


        except Exception as error:
            return {
                'status': 500,
                'message': "An error occurred during check-in/check-out",
                'error': str(error)
            }






    @http.route('/api/timeoff/hr-leave-type', type='json', auth='public', methods=['POST'], csrf=False)
    def get_hr_leave_type(self):
        try:
            data = json.loads(request.httprequest.data.decode())
            employee_id = data.get('employee_id')
            
            if not employee_id:
                return {"status":"error", "message": "Invalid or missing employee_id. Ensure it's a valid number."}

            # Search for employee record
            leave_records = request.env['hr.leave.type'].sudo().search([])
            
            if not leave_records:
                return {"status":"error", 'message': 'No hr leave type found'}

            # Prepare the response data
            leave_data = {
                'id': [leave.id for leave in leave_records], 
                'name': [leave.display_name for leave in leave_records], 
                'time_by': [leave.request_unit for leave in leave_records],
                'support_document': [leave.support_document for leave in leave_records],
                'requires_allocation': [leave.requires_allocation for leave in leave_records]
            }

            return {'status': 'success', 'data': leave_data} 

        except Exception as error:
            return {
                'status': 500,
                'message': 'An error occurred while fetching attendance location',
                'error': str(error)
            }






    @http.route('/api/timeoff/hr-leave', type='json', auth='public', methods=['POST'], csrf=False)
    def create_hr_leave(self):
        try:
            data = json.loads(request.httprequest.data.decode())

            employee_id = int(data.get('employee_id'))
            time_off_type = int(data.get('time_off_type'))
            date_from = data.get('date_from')
            date_to = data.get('date_to')
            custom_hours = data.get('custom_hours')
            hour_from = data.get('hour_from')
            hour_to = data.get('hour_to')
            description = data.get('description')

            supported_attachment_ids = data.get('supported_attachment_ids', [])

            
            # Validate input
            if not custom_hours:
                if not employee_id or not time_off_type or not date_from or not date_to:
                    return {"message": "Missing required fields"}
            else:
                if not employee_id or not time_off_type or not date_from or not hour_from or not hour_to:
                    return {"message": "Missing required fields for custom hours"}

            hr_leave_type = request.env['hr.leave.type'].sudo().search([ ('id', '=', time_off_type)], limit=1)
            if hr_leave_type.is_description:
                if not description:
                    return {"message": "The description field is required"}
            
            try:
                # Parse and localize datetime
                local_tz = pytz.timezone("Africa/Cairo")  # Replace with your local timezone

                # Convert local time to UTC
                local_dt_from = local_tz.localize(datetime.strptime(date_from, "%Y-%m-%d %H:%M:%S"))
                date_time_from_utc = local_dt_from.astimezone(pytz.utc).replace(tzinfo=None)  # convert to naive UTC
                date_from_only = date_time_from_utc.date()

                local_dt_to = local_tz.localize(datetime.strptime(date_to, "%Y-%m-%d %H:%M:%S"))
                date_time_to_utc = local_dt_to.astimezone(pytz.utc).replace(tzinfo=None)  # convert to naive UTC
                date_to_only = date_time_to_utc.date()

            except Exception as e:
                return {"message": f"Invalid date/time format: {str(e)}"}


            # Check if leave already exists
            hr_leave = request.env['hr.leave'].sudo().search([
                ('employee_id', '=', employee_id),
                ('request_date_from', '=', date_from_only),
            ], limit=1)

            if hr_leave:
                return {"message": "This Leave already exists."}

            # Prepare base leave data
            leave_data = {
                'employee_id': employee_id,
                'holiday_status_id': time_off_type,
                'date_from': date_time_from_utc,
                'date_to': date_time_to_utc ,
                'request_date_from': date_from_only,
                'request_date_to': date_to_only,
                # "name": description,
                'private_name': description,
                'all_employee_ids': [employee_id],
                'employee_company_id': request.env.company.id,
            }

            if custom_hours: 
                leave_data.update({
                    'request_hour_from': hour_from,
                    'request_hour_to': hour_to,
                    'request_unit_hours': True,
                })


            if supported_attachment_ids:
                leave_data['supported_attachment_ids'] = [(6, 0, supported_attachment_ids)]

            # Create the leave
            request.env['hr.leave'].sudo().create(leave_data)

            return {
                "success": True,
                "message": "Leave created successfully.",
            }

        except Exception as error:
            return {
                'status': 500,
                'message': "An error occurred during Hr Leave",
                'error': str(error)
            }


    @http.route('/api/attachment/upload-file', type='http', auth='public', methods=['POST'], csrf=False)
    def upload_file_attachment(self, **kwargs):
        try:
            uploaded_files = request.httprequest.files.getlist('file')
            if not uploaded_files:
                return request.make_json_response({"error": "No files uploaded"}, status=400)

            attachment_ids = []

            for uploaded_file in uploaded_files:
                file_content = uploaded_file.read()
                filename = uploaded_file.filename
                mimetype = uploaded_file.mimetype

                attachment = request.env['ir.attachment'].sudo().create({
                    'name': filename,
                    'datas': base64.b64encode(file_content),
                    'mimetype': mimetype,
                    'res_model': 'hr.leave',
                }) 

                attachment_ids.append(attachment.id)

            return request.make_json_response({
                "success": True,
                "attachment_ids": attachment_ids,
                "message": f"{len(attachment_ids)} file(s) uploaded successfully"
            })

        except Exception as e:
            return request.make_json_response({
                "error": str(e)
            }, status=500)


    @http.route('/api/timeoff/hr-leave/<int:leave_id>', type='json', auth='public', methods=['PUT'], csrf=False)
    def update_hr_leave2(self, leave_id):
        try: 
            data = json.loads(request.httprequest.data.decode())

            leave = request.env['hr.leave'].sudo().browse(leave_id)
            if not leave.exists():
                return {"message": "Leave not found"}
            
            # Prepare base leave data
            update_data={}
            
            try:
                # Parse and localize datetime
                local_tz = pytz.timezone("Africa/Cairo")  # Replace with your local timezone

                # Convert local time to UTC
                if 'date_from' in data:
                    local_dt_from = local_tz.localize(datetime.strptime(data.get('date_from'), "%Y-%m-%d %H:%M:%S"))
                    date_time_from_utc = local_dt_from.astimezone(pytz.utc).replace(tzinfo=None)  # convert to naive UTC
                    date_from_only = date_time_from_utc.date()
                    
                    update_data['date_from'] = date_time_from_utc
                    update_data['request_date_from'] = date_from_only
                    
                if 'date_to' in data:
                    local_dt_to = local_tz.localize(datetime.strptime(data.get('date_to'), "%Y-%m-%d %H:%M:%S"))
                    date_time_to_utc = local_dt_to.astimezone(pytz.utc).replace(tzinfo=None)  # convert to naive UTC
                    date_to_only = date_time_to_utc.date()
                    
                    update_data['date_to'] = date_time_to_utc
                    update_data['request_date_to'] = date_to_only

            except Exception as e:
                return {"message": f"Invalid date/time format: {str(e)}"}


            if 'time_off_type' in data:
                    update_data['holiday_status_id'] = int(data.get('time_off_type'))
            if 'description' in data:
                    update_data['private_name'] = data.get('description')

            if 'custom_hours' in data:
                if 'hour_from':
                    update_data['request_hour_from'] = data.get('hour_from')
                if 'hour_to' in data:
                        update_data['request_hour_to'] = data.get('hour_to')
                if 'custom_hours' in data:
                        update_data['request_unit_hours'] = data.get('custom_hours')

            # Update the leave
            leave.sudo().write(update_data)

            return {
                "success": True,
                "data": update_data,
                "message": "Leave updated successfully.",
            }

        except Exception as error:
            return {
                'status': 500,
                'message': "An error occurred while updating Hr Leave",
                'error': str(error)
            }
            

    @http.route('/api/timeoff/hr-leave/<int:leave_id>', type='json', auth='public', methods=['DELETE'], csrf=False)
    def delete_hr_leave(self, leave_id):
        try:
            leave = request.env['hr.leave'].sudo().browse(leave_id)
            if not leave.exists():
                return {"message": "Leave not found"}

            leave.unlink()

            return {
                "success": True,
                "message": "Leave deleted successfully"
            }
        except Exception as error:
            return {
                "status": 500,
                "message": "An error occurred while deleting Hr Leave",
                "error": str(error)
            }


    @http.route('/api/profile', type='json', auth='public', methods=['POST'], csrf=False)
    def get_employee_data(self):
        try:
            data = json.loads(request.httprequest.data.decode())
            employee_id = data.get('employee_id')
            
            if not employee_id:
                return {'status':"error", 'message': "Invalid or missing employee_id. Ensure it's a valid number."}

            # Search for employee record
            employee = request.env['hr.employee'].sudo().search([('id', '=', int(employee_id))], limit=1)
            
            if not employee:
                return {'status': 'error', 'message': 'Employee not found'}


            # Prepare the response data
            employee_data = {
                'id': employee.id,
                'name': employee.name,
                'email': employee.work_email,
                'employee_code': employee.code_num,
            }

            return {'status': 'success', 'data': employee_data}

        except Exception as error:
            return {
                'status': 500,
                'message': 'An error occurred while fetching profile data',
                'error': str(error)
            }



    @http.route('/api/payslip', type='json', auth='public', methods=['POST'], csrf=False)
    def payslipList(self, **post):        
        try:
            data = json.loads(request.httprequest.data.decode())
            employee_id = data.get('employee_id')

            if not employee_id:
                return {"status":"error", 'message': "Invalid or missing employee_id."}

            employee = request.env['hr.employee'].sudo().search([
                ('id', '=', int(employee_id))
                ], limit=1)

            hr_payslip_list = []
            
            for payslip in employee.slip_ids:
                if payslip.state in ['done','paid']: 
                    hr_payslip_list.append({
                        "id": payslip.id,
                        "number": payslip.number,
                        "batch": payslip.payslip_run_id.name if payslip.payslip_run_id else "",
                        "date_from": payslip.date_from.strftime("%Y-%m-%d"),
                        "date_to": payslip.date_to.strftime("%Y-%m-%d"),
                    })

            if not hr_payslip_list:
                return {"status": "success", "message": "No payslips found for this employee"}

                
            return {
                "status": "success",
                "payslips": hr_payslip_list,
            }
        
        except Exception as error:
            return request.make_json_response({
                'status': 500,
                'message': 'Error while downloading PDF',
                'error': str(error)
            }, status=500)



    @http.route('/api/payslip/review-download', type='http', auth='public', methods=['POST'], csrf=False)
    def review_download_payslip(self):
        try:
            data = json.loads(request.httprequest.data.decode())
            employee_id = data.get('employee_id')
            payslip_id = data.get('payslip_id')

            if not employee_id or not payslip_id:
                return request.make_json_response({"status":"error", 'message': "Invalid or missing employee_id or payslip_id field."}, status=400)

            employee_payslip = request.env['hr.payslip'].sudo().search([
                ('employee_id', '=', int(employee_id)), 
                ('id', '=', int(payslip_id))
            ], limit=1)

            if not employee_payslip or not employee_payslip.payslip_pdf:
                return request.make_json_response({
                    "message": "No Payslip Found for this employee or no payslip with this ID"
                }, status=500)

            pdf_data = base64.b64decode(employee_payslip.payslip_pdf)
            filename = employee_payslip.name or "payslip"

            return request.make_response(
                pdf_data,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="{filename}.pdf"'),
                ]
            )

        except Exception as error:
            return request.make_json_response({
                'status': 500,
                'message': 'Error while downloading PDF',
                'error': str(error)
            }, status=500)





    @route(['/public/attachment/<int:attachment_id>'], type='http', auth='public', cors='*')
    def public_attachment_download(self, attachment_id, **kwargs):
        attachment = request.env['ir.attachment'].sudo().browse(attachment_id)

        # Optional: Add your own access checks here
        if not attachment or not attachment.exists():
            return request.not_found()

        # Optional: Check if it's linked to hr.leave
        if attachment.res_model != 'hr.leave':
            return request.not_found()

        headers = [
            ('Content-Type', attachment.mimetype),
            ('Content-Disposition', content_disposition(attachment.name))
        ]
        return Response(base64.b64decode(attachment.datas), headers=headers)



    @http.route('/api/timeoff/hr-leave-list', type='json', auth='public', methods=['POST'], csrf=False)
    def get_hr_leave(self):
        try:
            data = json.loads(request.httprequest.data.decode())
            employee_id = data.get('employee_id')

            if not employee_id:
                return {"message": "Missing uid or status"}

            user = request.env['hr.employee'].sudo().search([('id', '=', employee_id), ('is_admin', '=', True)], limit=1)

            hr_leave = request.env['hr.leave'].sudo().search([('state', 'in', ['confirm']),
                                                                ('holiday_status_id.leave_validation_type','in',['manager', 'both'])])
            hr_leave_list = []
            
            if user:
                for rec in hr_leave:
                    for ele in rec.employee_ids:
                        # if ele.leave_manager_id.id == user.parent_user_id.id:
                        if ele.parent_id.id == user.id:
                            
                            # Get attachments linked to this leave
                            attachment_list = attachment_list_def(rec.id)
                            
                            hr_leave_list.append(
                                {
                                    "id":rec.id, 
                                    "name": rec.employee_id.name,
                                    "request_unit_hours": rec.request_unit_hours,
                                    "time_off_type": rec.holiday_status_id.name,
                                    "date_from": rec.request_date_from,
                                    "date_to": rec.request_date_to,
                                    "hour_from": rec.request_hour_from,
                                    "hour_to": rec.request_hour_to,
                                    "status": rec.state,
                                    # "description": rec.name,
                                    "description": rec.private_name or rec.display_name,
                                    "attachments": attachment_list
                                }
                            )
                            
            if not hr_leave_list:
                return {"message": "Not Found Hr Leave."}

            return {
                "success": True,
                "hr_leave": hr_leave_list,
            }

        except Exception as error:
            return {
                'status': 500,
                'message': "An error occurred during get Hr Leave",
                'error': str(error)
            }




    @http.route('/api/timeoff/hr-leave-approve', type='json', auth='public', methods=['POST'], csrf=False)
    def hr_leave_approve(self):
        try:
            data = json.loads(request.httprequest.data.decode())
            employee_id = data.get('employee_id')
            leave_id = int(data.get('leave_id'))
            approve_num = int(data.get('approve_num'))
            reason_refuse = data.get('reason_refuse')

            if not employee_id or not leave_id or not approve_num:
                return {'status': 500, "message": "Missing employee id or leave id or approve num or reason refuse"}

            # user = request.env['hr.employee'].sudo().search([('id', '=', employee_id), ('is_admin', '=', True)], limit=1)
            user = request.env['hr.employee'].sudo().browse(employee_id)
            if not user.is_admin:
                return {'status': 500, "message": "User not found or not admin"}

            hr_leave = request.env['hr.leave'].sudo().browse(leave_id)
                    
            if not hr_leave:
                return {'status': 500, "message": "Not Found Hr Leave."}

            if approve_num == 1:
                # if hr_leave.parent_id.user_id.id:
                if user.user_id:
                    # hr_leave.sudo().action_approve()
                    hr_leave.with_user(user.user_id).sudo().action_approve()
                else:
                    employees = hr_leave.employee_ids
                    leave_managers = employees.mapped('leave_manager_id.user_id')
                    for manager in leave_managers:
                        request.env['mail.activity'].sudo().create({
                            'res_model_id': request.env['ir.model']._get_id('hr.leave'),
                            'res_id': hr_leave.id,
                            'activity_type_id': request.env.ref('mail.mail_activity_data_todo').id,
                            'user_id': manager.id,
                            'summary': 'Approve Request',
                            'note': f'Approve the Leave <b>{", ".join(employees.mapped("name"))}</b>.',
                        })

                    # for employee in hr_leave.employee_ids:
                    #     if employee.leave_manager_id:
                    #         user.activity_schedule(
                    #             'mail.mail_activity_data_todo',
                    #             summary='Approve Request',
                    #             note=f'Approve the Leave <b>{employee.name}</b>.',
                    #             user_id=employee.leave_manager_id.id,
                    #         )
            elif approve_num == 2: 
                hr_leave.sudo().update({'name': reason_refuse})  
                hr_leave.action_refuse()
            else:
                return {
                    "success": False,
                    "show": True,
                    'message': "Enter Correct Number Action",                
                }
                
            return {
                "success": True,
                'status': hr_leave.state,
                'message': "successfully Done Request",
            }

        except Exception as error:
            return {
                'status': 500,
                'message': "An error occurred during Approve Hr Leave",
                'error': str(error)
            }




    @http.route('/api/hr-attendance-employee', type='json', auth='public', methods=['POST'], csrf=False)
    def get_hr_attendance(self):
        try:
            data = json.loads(request.httprequest.data.decode())
            employee_id = data.get('employee_id')

            if not employee_id:
                return {'status': 500, "message": "Missing uid or status"}

            existing_attendance = request.env['hr.draft.attendance'].sudo().search([ ('employee_id', '=', employee_id)])

            hr_attendance_list = []  
            
            if not existing_attendance:
                return {'status': 500, "message": "Not Attendance For This Employee."}


            # Get user's timezone or default to Cairo
            tz_name = request.env.context.get('tz') or 'Africa/Cairo'
            user_tz = pytz.timezone(tz_name)

            for rec in existing_attendance:
                # Parse datetime in UTC and convert to user time zone
                utc_dt = fields.Datetime.from_string(rec.name)
                localized_dt = pytz.UTC.localize(utc_dt).astimezone(user_tz)
                
                hr_attendance_list.append({
                    "id": rec.id,
                    "name": rec.employee_id.name,
                    "datetime": localized_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    # "datetime": rec.name,
                    "date": rec.date,
                    "attendance_status": rec.attendance_status,
                    "location_status": rec.location_status
                })
 
            if not hr_attendance_list:
                return {"message": "Not Attendance For This Employee."}

            return {
                "success": True,
                "hr_attendance": hr_attendance_list,
            }

        except Exception as error:
            return {
                'status': 500,
                'message': "An error occurred during get Hr Leave",
                'error': str(error)
            }




    @http.route('/api/hr-leave-employee', type='json', auth='public', methods=['POST'], csrf=False)
    def get_hr_leave_employee(self):
        try:
            data = json.loads(request.httprequest.data.decode())
            employee_id = data.get('employee_id')

            if not employee_id:
                return {"message": "Missing uid or status"}

            existing_leave = request.env['hr.leave'].sudo().search([ ('employee_ids', 'in', employee_id)])

            hr_leave_list = []
            
            if not existing_leave:
                return {'status': 500, "message": "Not leave For This Employee."}


            for rec in existing_leave:
                # Get attachments linked to this leave
                attachment_list = attachment_list_def(rec.id)
                hr_leave_list.append({
                    "id":rec.id, 
                    "name": rec.employee_id.name,
                    "request_unit_hours": rec.request_unit_hours,
                    "time_off_type": rec.holiday_status_id.name,
                    "date_from": rec.request_date_from,
                    "date_to": rec.request_date_to,
                    "hour_from": rec.request_hour_from,
                    "hour_to": rec.request_hour_to,
                    "status": rec.state,
                    # "description": rec.name,
                    "description": rec.private_name or rec.display_name,
                    "attachments": attachment_list
                })

            if not hr_leave_list:
                return {'status': 500, "message": "Not leave For This Employee."}

            return {
                "success": True,
                "hr_leave": hr_leave_list,
            }

        except Exception as error:
            return {
                'status': 500,
                'message': "An error occurred during get Hr Leave",
                'error': str(error)
            }




    @http.route('/api/timeoff/remaining-leave', type='json', auth='public', methods=['POST'], csrf=False)
    def get_remaining_leave(self):
        try:
            data = json.loads(request.httprequest.data.decode())
            employee_id = int(data.get('employee_id'))
            leave_type_id = int(data.get('leave_type_id'))

            employee = request.env['hr.employee'].sudo().browse(employee_id)
            leave_type = request.env['hr.leave.type'].sudo().browse(leave_type_id)

            if not employee or not leave_type:
                return {"status": "error", "message": "Invalid employee or leave type"}

            result = leave_type.get_employees_days([employee.id])
            leave_data = result.get(employee.id, {}).get(leave_type.id, {})

            remaining = leave_data.get('remaining_leaves', 0.0)
            unit = leave_type.request_unit  

            return {
                "status": "success",
                "data": {
                    "leave_type_id": leave_type.id,
                    "leave_type_name": leave_type.name,
                    "remaining": f"{remaining:.2f} {'hours' if unit == 'hour' else 'days'}"
                }
            }

        except Exception as e:
            return {
                "status": 500,
                "message": "Error fetching remaining leave",
                "error": str(e)
            }
