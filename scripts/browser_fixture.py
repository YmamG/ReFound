"""Disposable local-only browser fixture. Never run as a production service."""
import os, secrets, sys
from tempfile import TemporaryDirectory
from pathlib import Path
fixture=TemporaryDirectory(prefix='refound-browser-')
root=Path(fixture.name)
os.environ.update(DJANGO_SETTINGS_MODULE='ReFound.settings', DJANGO_SECRET_KEY=secrets.token_hex(48),DJANGO_DEBUG='False',DJANGO_SECURE_SSL_REDIRECT='False',DJANGO_STATIC_ROOT=str(root/'static'),DJANGO_ALLOWED_HOSTS='127.0.0.1,localhost,testserver',DJANGO_DB_PATH=str(root/'test.sqlite3'),DJANGO_MEDIA_ROOT=str(root/'media'), REFOUND_RATE_LIMIT='200')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import django
django.setup()
from django.conf import settings
# HTTP-only isolated test fixture; production cookie security is checked separately.
settings.SESSION_COOKIE_SECURE=False
settings.CSRF_COOKIE_SECURE=False
settings.LANGUAGE_COOKIE_SECURE=False
from django.core.management import call_command
call_command('migrate', verbosity=0)
call_command('collectstatic',interactive=False,verbosity=0)
from core.models import Report
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.core.files.base import ContentFile
from PIL import Image,ImageDraw
from io import BytesIO
items=[('Canvas backpack','bags','Olive','Main campus library','found'),('Wireless headphones','electronics','Cream','Student center','lost'),('Leather card holder','other','Brown','North entrance','found'),('House keys with blue tag','keys','Blue','Campus coffee shop','lost')]
for index,(title,category,color,location,kind) in enumerate(items):
    report=Report.objects.create(kind=kind,title=title,category=category,color=color,building="women" if index % 2 else "students",classroom="A-204" if index == 0 else "",location=location,event_date=timezone.localdate(),description='A '+color.lower()+' '+title.lower()+'. Reported near the public seating area. Please describe any distinctive details privately.',contact_method='email',contact_info='private@example.com',management_hash=make_password('browser-testing-owner-key'))
    # Original synthetic illustration solely for isolated browser checks; never user content.
    im=Image.new('RGB',(640,480),['#dce3ce','#e4dcd1','#e6cfb8','#c9dfe3'][index]);d=ImageDraw.Draw(im)
    if index==0:
        d.rounded_rectangle((220,110,420,400),radius=40,fill='#64795a');d.arc((270,65,370,170),180,360,fill='#3e5140',width=14);d.rounded_rectangle((240,280,400,375),radius=15,fill='#4a6148');d.line((250,300,390,300),fill='#a5b195',width=3)
    elif index==1:
        d.arc((190,85,450,350),180,360,fill='#75776e',width=25);d.rounded_rectangle((175,210,240,350),radius=25,fill='#f4f0e4');d.rounded_rectangle((400,210,465,350),radius=25,fill='#f4f0e4')
    elif index==2:
        d.rounded_rectangle((150,135,490,350),radius=25,fill='#8a5a3d');d.line((170,180,470,180),fill='#bd916f',width=4);d.rounded_rectangle((380,215,510,280),radius=15,fill='#71452f');d.ellipse((420,235,440,255),fill='#d7b16e')
    else:
        d.ellipse((220,120,340,240),outline='#b69a58',width=12);d.rectangle((272,230,290,370),fill='#c5ad6d');d.rectangle((287,330,320,350),fill='#c5ad6d');d.rounded_rectangle((340,240,420,340),radius=15,fill='#6596aa');d.line((320,220,365,270),fill='#b69a58',width=8)
    b=BytesIO();im.save(b,format='JPEG');report.image.save('browser-test.jpg',ContentFile(b.getvalue()),save=True)
from datetime import timedelta
archived = Report.objects.create(kind='found', title='Archived test notebook', category='other', building='students', location='Computing library', event_date=timezone.localdate(), description='An original fictional notebook report for archive browser testing.', contact_method='email', contact_info='private@example.com', management_hash=make_password(None))
Report.objects.filter(pk=archived.pk).update(created_at=timezone.now() - timedelta(days=61))
try:
    call_command('runserver','127.0.0.1:8000',use_reloader=False,verbosity=0)
finally:
    from django.db import connections
    connections.close_all()
    fixture.cleanup()
