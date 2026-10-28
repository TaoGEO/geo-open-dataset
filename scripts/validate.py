#!/usr/bin/env python3
"""Offline structural, count and residual checks. Optionally use private tables."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
sys.dont_write_bytecode = True
from anonymize import CONTACT_PATTERNS, URL, entity_context, load_table, registered_domain

FIELDS = {'batch_id','record_id','question_id','platform','model','sampled_at','round',
          'web_search_requested','web_search_observed','answer_text','sources','status','finish_reason'}

README_AUTHOR_ANCHOR = 'ORCID：[0009-0004-5104-1811](https://orcid.org/0009-0004-5104-1811)。'
README_AUTHOR_CONTACT = README_AUTHOR_ANCHOR + '公开联系方式：微信号 ' + 'Taomir' + '。'  # split so this file is not itself a hit


def public_files(root):
    return sorted(p for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts
                  and '__pycache__' not in p.relative_to(root).parts)


def validate(root, tables=None):
    root = Path(root)
    errors, counts = [], {}
    batches = list(csv.DictReader((root / 'batches.csv').open(encoding='utf-8', newline='')))
    expected = [f'B{n:02d}' for n in range(1,7)]
    if [r['batch_id'] for r in batches] != expected:
        errors.append('batch list must contain B01 through B06 once each')
    seen = set()
    for meta in batches:
        bid = meta['batch_id']; folder = root / 'data' / bid
        questions = list(csv.DictReader((folder / 'questions.csv').open(encoding='utf-8', newline='')))
        qids = {q['question_id'] for q in questions}
        if len(questions) != int(meta['题数']) or len(qids) != len(questions):
            errors.append(bid + ': question count or identifiers')
        rows = [json.loads(line) for line in (folder / 'answers.jsonl').read_text(encoding='utf-8').splitlines()]
        for row in rows:
            rid = row.get('record_id')
            if set(row) != FIELDS or row.get('batch_id') != bid or row.get('question_id') not in qids or rid in seen:
                errors.append(bid + ': schema/reference/unique record identifier')
            seen.add(rid)
            if not row['sampled_at'].endswith('+08:00'):
                errors.append(str(rid) + ': timezone')
            if any(type(row[k]) not in [bool, type(None)] for k in ['web_search_requested','web_search_observed']):
                errors.append(str(rid) + ': network boolean')
            for index,s in enumerate(row['sources'],1):
                if set(s) != {'order','url','title','kind','published_at'} or s['order'] != index:
                    errors.append(str(rid) + ': source structure/order')
                if s.get('kind') not in ('citation', 'search_result'):
                    errors.append(str(rid) + ': source kind')
                if s['url'] is not None and not re.fullmatch(r'https://[A-Za-z0-9.-]+',s['url']):
                    errors.append(str(rid) + ': source URL')
            for url in URL.findall(row['answer_text']):
                if not re.fullmatch(r'https://[A-Za-z0-9.-]+',url):
                    errors.append(str(rid) + ': body URL')
        valid = sum(r['status'] == 'valid' for r in rows)
        failed = len(rows) - valid
        if valid != int(meta['有效回答数']) or failed != int(meta['失败数']):
            errors.append(bid + ': answer count')
        counts[bid] = {'questions':len(questions),'answers':len(rows),'valid':valid,'failed':failed}
    residue = {'contacts':0,'sensitive_tokens':0,'key_shaped_strings':0,
               'dictionary':0 if tables else None,'people':0 if tables else None}
    sensitive = [''.join(chr(c) for c in codes) for codes in [
        [115,107,45],[66,101,97,114,101,114],[97,112,105,95,107,101,121],
        [65,117,116,104,111,114,105,122,97,116,105,111,110],[65,99,99,101,115,115,75,101,121]]]
    files = public_files(root)
    public_names = root / 'data' / 'B01' / 'public-names.csv'
    aliases, people = [], []
    if tables:
        for bid in expected:
            t = load_table(Path(tables) / (bid + '.json'))
            aliases.extend(v['text'] for e in t['entities'] for v in e['variants'])
            people.extend(t.get('people', []))
    pattern = re.compile('|'.join(re.escape(s) for s in sorted(set(aliases),key=lambda s:(-len(s),s)))) if aliases else None
    for path in files:
        if path.suffix == '.ots':
            continue
        text = path.read_text(encoding='utf-8')
        # SHA-256 commitments can contain digit runs; they are not contacts.
        contact_text = re.sub(r'(?<![A-Za-z0-9])[a-fA-F0-9]{64}(?![A-Za-z0-9])', '', text)
        # Sole exception: the author's own authorized WeChat ID, exactly once, right after
        # the ORCID in README.md. Any other contact text anywhere is still counted.
        if path == root / 'README.md':
            contact_text = contact_text.replace(README_AUTHOR_CONTACT, README_AUTHOR_ANCHOR, 1)
        n = sum(len(re.findall(rule,contact_text)) for _,rule in CONTACT_PATTERNS)
        residue['contacts'] += n
        token_hits = sum(len(re.findall(re.escape(token),text,re.I)) for token in sensitive)
        residue['sensitive_tokens'] += token_hits
        # Article URLs in citation metadata may have long, ordinary path slugs.
        key_text = re.sub(r'https://taomir\.cn/articles/[a-z0-9-]+/?', '', text)
        keys = re.findall(r'(?<![A-Za-z0-9])[A-Za-z0-9_+/=-]{40,}(?![A-Za-z0-9])',key_text)
        key_hits = sum(not re.fullmatch(r'[a-fA-F0-9]{64}',s) and not re.fullmatch(r'[-=]+',s) for s in keys)
        residue['key_shaped_strings'] += key_hits
        person_hits = sum(text.count(name) for name in set(people))
        if tables:
            residue['people'] += person_hits
        if pattern and path != public_names:
            bid = next((part for part in path.relative_to(root).parts if part in expected), None)
            n = sum(entity_context(text, m.start(), m.end(), m.group(0), bid) for m in pattern.finditer(text))
            residue['dictionary'] += n
        if n or token_hits or key_hits or person_hits:
            errors.append(str(path.relative_to(root)) + ': residual text detected')
    if any(residue.values()):
        errors.append('residual counts are nonzero')
    if len(list(csv.DictReader(public_names.open(encoding='utf-8',newline='')))) != 14:
        errors.append('public name count must be 14')
    release = root / 'proofs' / 'release-sha256.txt'
    if release.exists():
        for line in release.read_text(encoding='utf-8').splitlines():
            digest,relative = line.split('  ',1)
            file = root / relative
            if not file.exists() or hashlib.sha256(file.read_bytes()).hexdigest() != digest:
                errors.append('release checksum: ' + relative)
    return {'batches':len(batches),'counts':counts,'total_answers':sum(c['answers'] for c in counts.values()),
            'outside_batches':sum(1 for p in (root/'data').iterdir() if p.name not in expected),
            'residuals':residue,'files':len(files),'errors':errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--tables',type=Path)
    args=parser.parse_args()
    result=validate(args.root,args.tables)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(int(bool(result['errors'])))


if __name__ == '__main__':
    main()
