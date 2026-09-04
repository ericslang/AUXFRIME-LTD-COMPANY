import os
import django
from django.test import RequestFactory

os.environ.setdefault('DJANGO_SETTINGS_MODULE','tracker.settings')
django.setup()

from django.contrib.auth import get_user_model
from tracker import views

User = get_user_model()
user = User.objects.first()
if not user:
    user = User.objects.create_user('testuser', 'test@example.com', 'testpass')

rf = RequestFactory()
request = rf.get('/')
request.user = user

resp = views.dashboard(request)
html = resp.content.decode('utf-8')
print('status', resp.status_code)
print('has top member savers?', 'Top member savers' in html)
idx = html.find('Top member savers')
if idx!=-1:
    print(html[idx:idx+200])
else:
    print('section not found in rendered HTML')
