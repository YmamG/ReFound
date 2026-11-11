"""Build Django Arabic catalogs from editable UTF-8 JSON, using only stdlib.
Run after editing locale/ar/messages.json. No gettext system package is required.
"""
import json
from pathlib import Path
import struct

root = Path(__file__).resolve().parents[1]
source = root / 'locale/ar/messages.json'
messages = json.loads(source.read_text(encoding='utf-8'))
messages[''] = 'Content-Type: text/plain; charset=UTF-8\nLanguage: ar\nPlural-Forms: nplurals=6; plural=n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 && n%100<=10 ? 3 : n%100>=11 && n%100<=99 ? 4 : 5;\n'
keys = sorted(messages)
originals = b''
translations = b''
original_table = []
translation_table = []
base = 28 + 16 * len(keys)
for key in keys:
    encoded = key.encode('utf-8')
    original_table.append((len(encoded), base + len(originals)))
    originals += encoded + b'\0'
for key in keys:
    encoded = messages[key].encode('utf-8')
    translation_table.append((len(encoded), base + len(originals) + len(translations)))
    translations += encoded + b'\0'
target = source.parent / 'LC_MESSAGES'
target.mkdir(exist_ok=True)
header = struct.pack('<7I', 0x950412de, 0, len(keys), 28, 28 + 8 * len(keys), 0, 0)
tables = b''.join(struct.pack('<2I', *row) for row in original_table + translation_table)
(target / 'django.mo').write_bytes(header + tables + originals + translations)
po = '# Generated from ../messages.json by scripts/compile_translations.py.\n'
for key in keys:
    po += '\nmsgid ' + json.dumps(key, ensure_ascii=False) + '\nmsgstr ' + json.dumps(messages[key], ensure_ascii=False) + '\n'
(target / 'django.po').write_text(po, encoding='utf-8')
print(f'Compiled {len(keys) - 1} Arabic messages.')
