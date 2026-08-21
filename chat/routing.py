from django import forms

def websocket_urlpatterns(request):
    user_id = request.session.get('reset_user_id')
    error = None