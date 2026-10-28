#!/usr/bin/env python3
"""Guard the empty-bank distribution; not a complete personal-data detector."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
idx=json.loads((root/'banks/index.json').read_text())
assert idx['private_style_bank']==[] and idx['journal_standards_bank']==[], 'Public index must stay empty'
for folder in ('private-style','journal-standards'):
 assert not any(p.is_file() for p in (root/'banks'/folder).rglob('*')), 'Populated bank must remain outside public checkout'
for p in root.rglob('*'):
 if '.git' in p.parts or '__pycache__' in p.parts or not p.is_file(): continue
 assert p.suffix.lower() not in ('.docx','.pdf','.zip'), 'Source/archive artifact in public distribution'
 if p.suffix in ('.md','.json','.py','.yaml'):
  assert ('/'+'Users'+'/') not in p.read_text(), 'Local user path in public file'
print('Public scaffold checks passed; manually review newly added content before publication.')
