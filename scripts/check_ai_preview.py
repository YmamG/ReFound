"""Optional offline AI smoke with disposable data. No downloads or production writes."""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

parser=argparse.ArgumentParser()
parser.add_argument('--model-path',required=True)
args=parser.parse_args()
with TemporaryDirectory(prefix='refound-ai-smoke-') as temporary:
    os.environ.update(DJANGO_SETTINGS_MODULE='ReFound.settings',DJANGO_DEBUG='True',
        DJANGO_SECRET_KEY=secrets.token_hex(48),DJANGO_DB_PATH=str(Path(temporary)/'test.sqlite3'),
        REFOUND_AI_PREVIEW_ENABLED='True',REFOUND_AI_MODEL_PATH=str(Path(args.model_path).resolve()))
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    import django
    django.setup()
    from django.core.management import call_command
    call_command('migrate',verbosity=0)
    from core.models import Report
    from core.services.ai_matching import model,preview_matches
    from django.utils import timezone
    def report(title,kind,color,building='students'):
        return Report.objects.create(title=title,kind=kind,color=color,building=building,
            description='',category='bags',location='Library',event_date=timezone.localdate(),
            contact_method='email',contact_info='fictional@example.test',management_hash='!')
    source=report('حقيبة لابتوب سوداء','lost','أسود')
    report('Black laptop bag','found','black')
    report('Red backpack','found','red')
    report('Leather wallet','found','brown')
    hidden=report('Hidden black laptop bag','found','black');hidden.is_hidden=True;hidden.save()
    report('Other building black laptop bag','found','black','women')
    start=perf_counter();model();startup=perf_counter()-start
    start=perf_counter();first=preview_matches(source);cold=perf_counter()-start
    start=perf_counter();second=preview_matches(source);warm=perf_counter()-start
    assert first['mode']=='ai' and second['mode']=='ai'
    assert len(second['matches'])==3
    assert all(not match.report.is_hidden and match.report.building=='students' for match in second['matches'])
    try:
        import resource
        peak=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,1)
    except ImportError:
        peak=None
    output={'model':'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
        'device':'CPU','threads':2,'model_startup_seconds':round(startup,3),
        'first_4_text_batch_seconds':round(cold,3),'warm_4_text_batch_seconds':round(warm,3),
        'process_peak_rss_mib_linux':peak,
        'snapshot_storage_mib':round(sum(p.stat().st_size for p in Path(args.model_path).rglob('*') if p.is_file())/1024**2,1),
        'synthetic_smoke_only_not_accuracy':True,
        'results':[{'title':m.report.title,'blend':m.score,'rule':m.rule_score,'cosine':m.cosine} for m in second['matches']]}
    print(json.dumps(output,ensure_ascii=False,indent=2))
    from django.db import connections
    connections.close_all()
