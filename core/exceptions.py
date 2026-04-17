from rest_framework.views import exception_handler
from rest_framework.response import Response

def core_exception_handler(exc, context):
    # Call standard DRF exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Standardize the error response
        message = "Validation Error"
        if response.status_code == 404:
            message = "Not Found"
        elif response.status_code == 403:
            message = "Permission Denied"
        elif response.status_code == 401:
            message = "Authentication Required"
        
        # We can also pull the first error message if available
        if isinstance(response.data, dict) and 'detail' in response.data:
            message = response.data.pop('detail')
        elif isinstance(response.data, list) and len(response.data) > 0:
            message = str(response.data[0])

        response.data = {
            'status': response.status_code,
            'message': message,
            'data': response.data
        }

    return response
