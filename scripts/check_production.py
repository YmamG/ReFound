"""Check production behavior using disposable storage. Never deploys."""
import os,secrets,sys
from tempfile import TemporaryDirectory
from pathlib import Path
fixture=TemporaryDirectory(prefix='refound-production-')
root=Path(fixture.name)
os.environ.update(DJANGO_SETTINGS_MODULE='ReFound.settings', DJANGO_SECRET_KEY=secrets.token_hex(48),DJANGO_DEBUG='False',DJANGO_SECURE_SSL_REDIRECT='True',DJANGO_HSTS_SECONDS='3600',DJANGO_HSTS_INCLUDE_SUBDOMAINS='False',DJANGO_HSTS_PRELOAD='False',DJANGO_ALLOWED_HOSTS='localhost,127.0.0.1,testserver',DJANGO_DB_PATH=str(root/'test.sqlite3'),DJANGO_MEDIA_ROOT=str(root/'media'),DJANGO_STATIC_ROOT=str(root/'static'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import django
django.setup()
from django.core.management import call_command
from django.test import Client,override_settings
from django.conf import settings
call_command('migrate',verbosity=0)
call_command('collectstatic',interactive=False,verbosity=0)
call_command('check',deploy=True)
with override_settings(SECURE_HSTS_INCLUDE_SUBDOMAINS=True,SECURE_HSTS_PRELOAD=True):
    call_command('check',deploy=True,fail_level='WARNING')
client=Client()
r=client.get('/')
assert r.status_code==301 and r.url.startswith('https://')
r=client.get('/',secure=True)
assert r.status_code==200, r.status_code
assert 'max-age=3600' in r['Strict-Transport-Security']
assert settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE
assert r.cookies[settings.REFOUND_DEVICE_COOKIE]['secure']
assert r.cookies[settings.REFOUND_DEVICE_COOKIE]['httponly']
assert 'private' in r['Cache-Control']
arabic = client.get('/', secure=True, HTTP_ACCEPT_LANGUAGE='ar')
assert 'lang="ar" dir="rtl"' in arabic.content.decode()
assert 'البحث عن المفقودات' in arabic.content.decode()
language = client.post('/i18n/setlang/', {'language': 'en', 'next': '/'}, secure=True)
assert language.cookies[settings.LANGUAGE_COOKIE_NAME]['secure']
assert language.cookies[settings.LANGUAGE_COOKIE_NAME]['httponly']
from django.contrib.staticfiles.storage import staticfiles_storage
for name in ['css/tokens.css','css/style.css','css/story.css','css/match-game.css','js/match-game.js','images/return-story.webp','images/search-story.webp','js/main.js','images/icons.svg','images/belongings-illustration.webp','images/favicon.svg','fonts/inter-latin-400.woff2','fonts/inter-latin-500.woff2','fonts/noto-arabic-400.woff2','fonts/noto-arabic-500.woff2']:
    url=staticfiles_storage.url(name)
    r=client.get(url,secure=True)
    assert r.status_code==200,(url,r.status_code)
    assert 'immutable' in r['Cache-Control'],(url,r.headers)
    r.close()
assert client.get('/media/anything.jpg',secure=True).status_code==404
assert client.get('/not-found/',secure=True).status_code==404
assert not any(module.split('.')[0] in {'torch','transformers','sentence_transformers','open_clip'} for module in sys.modules)
call_command('makemigrations',check=True,dry_run=True,verbosity=1)
print('Production smoke passed: HTTPS redirect, secure cookies, HSTS, all hashed assets, immutable caching, protected media, branded 404, no ML imports.')

from django.db import connections
connections.close_all()
fixture.cleanup()
