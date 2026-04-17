from rest_framework.renderers import JSONRenderer

class CoreJSONRenderer(JSONRenderer):
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response')
        status_code = response.status_code

        # If it's already an error handled by our exception handler, 
        # it might already have the format. Let's check.
        if isinstance(data, dict) and 'status' in data and 'message' in data:
            return super().render(data, accepted_media_type, renderer_context)

        # Default message based on status code
        message = "Request successful"
        if status_code >= 400:
            message = "An error occurred"
            
        # Check if the view provided a custom message in the data
        if isinstance(data, dict) and 'message' in data:
            message = data.pop('message')

        # Wrap the data
        wrapped_data = {
            'status': status_code,
            'message': message,
            'data': data
        }

        return super().render(wrapped_data, accepted_media_type, renderer_context)
