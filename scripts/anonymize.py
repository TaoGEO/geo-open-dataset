#!/usr/bin/env python3
"""Deterministic offline export. Original paths and entity tables are private inputs.

Usage: python3 scripts/anonymize.py --sources /private/source-map.json \
       --tables /private/code-tables --output /path/to/dataset
No network access or third-party packages are used.
"""
import argparse
import csv
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo


URL = re.compile(r'https?://[^\s<>\[\]()（）〔〕"`“”‘’，。；！、]+', re.I)
BARE_URL = re.compile(r'(?<![A-Za-z0-9@_./-])(?:[A-Za-z][A-Za-z0-9-]*\.)+(?:com|net|org|cn|hk|edu|io|uk|au|ca|us)(?:\.[A-Za-z]{2,})?(?:[/?#][^\s<>\[\]()（）〔〕"`“”‘’，。；！、]*)?', re.I)
MULTI_SUFFIX = set('com.cn net.cn org.cn gov.cn edu.cn ac.cn com.hk org.hk edu.hk '
                  'com.tw org.tw edu.tw co.uk org.uk ac.uk gov.uk com.au net.au '
                  'edu.au co.nz co.jp co.kr com.sg org.sg com.br co.in co.za sh.cn ah.cn'.split())
CONTACT_PATTERNS = [
    ('电话', r'(?<!\d)(?:\*\*)?1[3-9][0-9]{1,8}[*＊xX]{2,}(?!\d)'),
    ('邮箱', r'(?<![A-Za-z0-9_.+-])[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'),
    ('微信', r'(?i)(?:微信(?:号)?|微[信訊]|[Vv][Xx]|[Ww][Xx]|[Ww]e[Cc]hat)\s*[：:=]?\s*[A-Za-z][A-Za-z0-9_-]{4,19}'),
    ('QQ', r'(?i)QQ\s*(?:号|号码)?\s*[：:=]?\s*[1-9][0-9]{4,11}'),
    ('电话', r'(?<![\w+])\+[1-9][0-9]{0,2}[ -]*(?:\(0\)[ -]*)?(?:[0-9][ -]*){7,12}[0-9](?!\d)'),
    ('电话', r'(?<!\d)(?:\+?86[-\s\u2010-\u2015\uff0d]?)?1[3-9][0-9](?:[-\s\u2010-\u2015\uff0d]?[0-9]){8}(?!\d)'),
    ('电话', r'(?<!\d)(?:400|800)[-\s\u2010-\u2015\uff0d]?[0-9]{3}[-\s\u2010-\u2015\uff0d]?[0-9]{4}(?!\d)'),
    ('电话', r'(?<!\d)(?:\(?0[0-9]{2,3}\)?[-\s\u2010-\u2015\uff0d]?[0-9]{7,8})(?:[-转][0-9]{1,6})?(?!\d)'),
    ('电话', r'(?:电话|热线|座机|联系方式|咨询电话)\s*[：:=]?\s*[0-9０-９][0-9０-９\s\u2010-\u2015\uff0d()-]{4,}'),
]


def entity_context(text, start, end, spelling, batch_id=None):
    """Keep attested geographic, media and common-word collisions in context."""
    left, right = text[max(0, start - 12):start], text[end:end + 18]
    if re.fullmatch(r'[\u4e00-\u9fff][·・•｜| \u3000—-]*[\u4e00-\u9fff]', spelling):
        spelling = re.sub(r'[·・•｜| \u3000—-]', '', spelling)
    if spelling == '\x4d\x49\x54' and batch_id is None and re.search(r'code|代码|license|许可', left + right, re.I):
        return False
    if re.search(r'[A-Za-z]', spelling):
        if start and re.match(r'[A-Za-z]', text[start - 1]) and re.match(r'[A-Za-z]', spelling):
            return False
        version_suffix = bool(re.match(r'[vV]\d', right))
        if end < len(text) and re.match(r'[A-Za-z\u00c0-\u024f]', text[end]) and re.search(r'[A-Za-z]$', spelling) and not version_suffix:
            return False
        if re.fullmatch(r'[A-Za-z0-9]+', spelling) and ((start and text[start-1].isalnum() and text[start-1].isascii()) or (end < len(text) and text[end].isalnum() and text[end].isascii() and not version_suffix)):
            return False
    if re.fullmatch(r'\u5ddd[·・•｜| \u3000—-]*\u5927', spelling) and (left.endswith('新') and right.startswith('源')):
        return False
    if spelling == '\x44\x41\x50' and batch_id != 'B05':
        return False
    if spelling == '\x54\x33' and batch_id != 'B02':
        return False
    if spelling.lower() == '\x33\x6d' and (right.startswith('m') or (left and left[-1].isdigit())):
        return False
    if spelling == '\u592a\u53e4' and right.startswith('里'):
        return False
    if spelling == '\u5927\u4f17' and (right.startswith(('点评', '网', '化')) or batch_id != 'B05'):
        return False
    if spelling == '\u65b0\u901a' and (right.startswith('路') or re.match(r'[东南西北][一二三四五0-9]*路',right)):
        return False
    if spelling == '\u65b0\u901a' and left.endswith('高') and right.startswith('勤'):
        return False
    if spelling == '\u7406\u60f3' and (batch_id != 'B05' or not re.match(r'(?:L[6789]|L系列|i[68]|ONE|MEGA|汽车|车型|车主|新能源|等|[、/，])', right)):
        return False
    if spelling == '\u5929\u901a' and right.startswith(('知', '勤')):
        return False
    if spelling == '\u5929\u7a7a' and not (left.endswith('比如') and right.startswith('、')):
        return False
    if spelling == '\u8309\u8389' and right.startswith('香'):
        return False
    if spelling == '\u5927\u5496' and not right.startswith('这类'):
        return False
    if spelling == '\u591a\u5927' and (batch_id != 'B04' or not re.match(r'偏|[、/]|等', right)):
        return False
    if spelling == '\u4e2d\u5927' and (batch_id != 'B04' or not right.startswith('/')):
        return False
    if spelling == '\u79d1\u5927' and (left.endswith(('学', '本')) or right.startswith('类')):
        return False
    if spelling == '\u897f\u5317' and not right.startswith('机械博士'):
        return False
    if spelling == '\u6210\u7535' and right.startswith(('子', '影')):
        return False
    if spelling == '\u65b0\u5357' and left.endswith('高'):
        return False
    if spelling == '\u62db\u5546' and right.startswith(('手册', '引资')):
        return False
    if spelling == '\u884c\u7b80' and left.endswith('进') and right.startswith(('短', '单', '化')):
        return False
    if spelling == '\u4e2d\u6d77' and (left.endswith('地') or (left.endswith('城市') and right.startswith('景'))):
        return False
    if re.fullmatch(r'\u5a5a\u524d\s*MV\s*\u53cc\u5f71\u50cf', spelling):
        return False
    if spelling in ('\u6089\u5c3c', '\u58a8\u5c14\u672c'):
        line_left = text[max(text.rfind('\n',0,start),text.rfind('\\n',0,start))+1:start]
        if not re.search(r'澳洲八大（|IT / 工程（尤其', line_left):
            return False
    if spelling in ('\u591a\u4f26\u591a', '\u8499\u7279\u5229\u5c14'):
        line_left = text[max(text.rfind('\n',0,start),text.rfind('\\n',0,start))+1:start]
        if '比如AI→' not in line_left:
            return False
    if spelling == '\u91cc\u6602' and '目标城市' in text[max(0,start-25):start]:
        return False
    if spelling == '\u65b9\u53ef' and not re.match(r'(?:软件|进销存|出入库|仓库|ERP|这类|[）)、/])', right, re.I):
        return False
    if spelling == '\u62e9\u884c' and left.endswith('选'):
        return False
    if spelling == '\u5408\u601d' and left.endswith('组'):
        return False
    if spelling == '\u52a0\u6210' and left.endswith('增') and right.startswith('本'):
        return False
    if spelling == '\u5927\u91d1' and left.endswith('四') and right.startswith('刚'):
        return False
    if spelling == '\u8272\u8272' and ((left.endswith('颜') and right.startswith('差')) or (left.endswith('实') and right.startswith('卡'))):
        return False
    if spelling == '\u4f18\u8d8a' and not right.startswith(('外籍', '留学', '教育')):
        return False
    if spelling == '\u591a\u5ba2' and right.startswith('户'):
        return False
    if spelling == '\u6279\u96f6\u901a' and right.startswith('用'):
        return False
    if spelling == '\u5546\u8d38\u901a' and right.startswith('用'):
        return False
    if spelling == '\u4e91\u8f6f' and right.startswith('件'):
        return False
    if spelling == '\u9f99\u6e56' and left.endswith('青'):
        return False
    if spelling == '\u552f\u4e00' and not (left.endswith(('、', '/', '（', '(')) and right.startswith(('等', '、', '/', '）', ')'))):
        return False
    if spelling == '\u60a6\u52a8' and right.startswith('新城'):
        return False
    if spelling == '\u897f\u5cb8' and left.endswith('兴隆湖'):
        return False
    if spelling == '\u7c73\u5170' and left.endswith('卡其'):
        return False
    if spelling == '\u91d1\u6570\u636e' and left.endswith('资'):
        return False
    if spelling == '\u9646\u8096TOD' and (left.endswith(('紧邻', '板块（')) or right.startswith('站')):
        return False
    if spelling == '\u957f\u4f4f' and not (left.endswith('_') or right.startswith(('玖川', '·', '集团', '地产'))):
        return False
    if spelling == '\u5f53\u4ee3' and not (left.endswith(('/', '、', '+')) or right.startswith('卫浴')):
        return False
    if spelling == '\u6613\u5448' and left.endswith('容') and right.startswith('现'):
        return False
    if spelling == '\u6613\u5ea6' and left.endswith(('简', '难')):
        return False
    if spelling == '\u70b9\u7279' and left.endswith('地') and right.startswith('色'):
        return False
    if spelling == '\u65b0\u901a' and left.endswith('港') and right.startswith('常'):
        return False
    if spelling == '\u9f0e\u65b0' and left.endswith('问'):
        return False
    if spelling == '\u7f8e\u7684' and (left.endswith(('优','完','精','唯','审','赞')) or (left.endswith('更') and right.startswith(('”', '」')))):
        return False
    if spelling == '\u9ad8\u4eea' and right.startswith('式'):
        return False
    if spelling == '\u9ad8\u6295' and right.startswith(('资', '入')):
        return False
    if spelling == '\u5317\u5cb8' and batch_id != 'B03' and not right.startswith(('映画', '摄影', '影像')):
        return False
    if spelling == '\u901f\u8fbe' and batch_id not in ['B02', None] and not right.startswith(('软件', 'ERP')):
        return False
    if spelling == '\u6d6a\u6f6e' and batch_id not in ['B02', None] and not right.startswith(('云', '软件', '集团', '海岳')):
        return False
    if re.fullmatch(r'[\u4e00-\u9fff]{2,4}', spelling) and right.startswith(('路', '街', '大道', '板块', '地铁站')):
        return False
    if re.fullmatch(r'[\u4e00-\u9fff]{2,}', spelling) and right.startswith('站'):
        return False
    return True


def load_table(path):
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    return json.loads('\n'.join(lines[1:]))


def registered_domain(url):
    host = (urlsplit(url).hostname or '').lower().strip('.')
    try:
        host = host.encode('idna').decode('ascii')
    except UnicodeError:
        pass
    labels = host.split('.')
    n = 3 if '.'.join(labels[-2:]) in MULTI_SUFFIX else 2
    return '.'.join(labels[-n:])


def bool_search(parameters):
    if parameters.get('enable_search') is not None:
        return bool(parameters['enable_search'])
    if 'tools' in parameters:
        return any('search' in t.get('type', '') for t in parameters['tools'])
    return None


def source_date(item):
    """Preserve absolute dates from saved source metadata, never from titles."""
    for metadata in (item, item.get('original') or {}):
        for key in ('published_at', 'publish_time', 'page_age'):
            value = metadata.get(key)
            if not isinstance(value, str) or not value.strip():
                continue
            value = value.strip()
            match = re.fullmatch(r'(\d{4})年(\d{2})月(\d{2})日 (\d{2}):(\d{2}):(\d{2})\(CST\) 星期.', value)
            try:
                if match:
                    return datetime(*map(int, match.groups()), tzinfo=ZoneInfo('Asia/Shanghai')).isoformat()
                parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
                if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                    return parsed.date().isoformat()
                if parsed.tzinfo is not None:
                    return parsed.isoformat()
            except ValueError:
                pass
    return None


def source_items(citations, search_results=()):
    """Keep list membership, order and duplicates from the saved protocol."""
    return [{'order': i, 'url': item.get('url') or '', 'title': item.get('title') or '',
             'kind': kind, 'published_at': source_date(item)}
            for i, (kind, item) in enumerate(
                [('citation', item) for item in citations or []] +
                [('search_result', item) for item in search_results or []], 1)]


def read_original(config, batch_id):
    """Project only the permitted sampling fields; never export response payloads."""
    path = Path(config['path'])
    questions, records = {}, []
    if path.is_file():
        obj = json.loads(path.read_text(encoding='utf-8'))
        for q in obj['questions']:
            qid = str(q['question_id'])
            questions[qid] = {'question_id': qid, '题型或分类': q.get('family'),
                              'question_text': q.get('text', q.get('question')),
                              '是否点名题': bool(q.get('target_named'))}
        for raw in obj['records']:
            s = raw['sampling']
            calls = s.get('web_search_call_count')
            observed = s.get('web_search_transport_verified')
            if observed is None:
                observed = False if s.get('web_search_contract_status') == 'verified_no_search' else (calls > 0 if calls is not None else None)
            records.append({
                'batch_id': batch_id, 'question_id': str(raw['question_id']),
                'platform': raw['platform'], 'model': s.get('model'),
                'sampled_at': s.get('started_at'), 'round': int(raw['round']),
                'web_search_requested': s.get('web_search_requested'),
                'web_search_observed': observed,
                'answer_text': s.get('answer_text_raw') or '',
                'sources': source_items(s.get('citation_items', [])),
                'status': 'valid' if s.get('status') == 'valid' else 'failed',
                'finish_reason': None,
            })
    else:
        protocol = json.loads((path / 'protocol.json').read_text(encoding='utf-8'))
        for f in sorted((path / 'sampled').rglob('*.json')):
            raw = json.loads(f.read_text(encoding='utf-8'))
            qid = str(raw['question_id'])
            questions[qid] = {'question_id': qid, '题型或分类': raw.get('family'),
                              'question_text': raw['question'],
                              '是否点名题': bool(raw.get('target_named'))}
            platform = raw.get('platform', config.get('default_platform'))
            params = protocol.get('parameters', protocol.get('doubao_parameters', {}))
            if platform in params:
                params = params[platform]
            requested = raw.get('search_requested', bool_search(params))
            calls = raw.get('search_call_count')
            response = raw.get('raw_response') or {}
            choices = response.get('choices') or [{}]
            finish = choices[0].get('finish_reason') or response.get('stop_reason')
            if finish is None and response.get('status'):
                incomplete = response.get('incomplete_details') or {}
                finish = incomplete.get('reason') or response['status']
            sources = source_items(raw.get('citations'), raw.get('search_results'))
            answer = raw.get('answer') or ''
            valid = bool(answer.strip()) and raw.get('success') is not False
            records.append({
                'batch_id': batch_id, 'question_id': qid,
                'platform': platform, 'model': raw.get('model'),
                'sampled_at': raw.get('sampled_at'), 'round': int(raw['repeat']),
                'web_search_requested': requested,
                'web_search_observed': calls > 0 if calls is not None else None,
                'answer_text': answer,
                'sources': sources,
                'status': 'valid' if valid else 'failed', 'finish_reason': finish,
            })
    records.sort(key=lambda r: (r['question_id'], r['platform'], r['round']))
    for r in records:
        r['record_id'] = f"{batch_id}-{r['question_id']}-{r['platform']}-R{r['round']:02d}"
        if r['sampled_at']:
            r['sampled_at'] = datetime.fromisoformat(r['sampled_at'].replace('Z', '+00:00')).astimezone(ZoneInfo('Asia/Shanghai')).isoformat()
    return [questions[q] for q in sorted(questions)], records


def make_transform(table):
    aliases = {v['text']: v['code'] for entity in table['entities'] for v in entity['variants']}
    pattern = re.compile('|'.join(re.escape(s) for s in sorted(aliases, key=lambda s: (-len(s), s)))) if aliases else None
    people = table.get('people', [])
    person_pattern = re.compile('|'.join(re.escape(s) for s in sorted(people, key=lambda s: (-len(s), s)))) if people else None
    own_domains = table.get('brand_domains', {})

    def domain(url):
        if not url:
            return None
        root = registered_domain(url)
        if not root:
            return None
        entity = own_domains.get(root)
        return 'https://' + ('brand-' + entity + '.invalid' if entity else root)

    def text(value):
        value = str(value)
        urls = []
        def hide(match):
            link = match.group(0)
            urls.append(domain(link if link.lower().startswith(('http://','https://')) else 'https://' + link))
            return '\x00' + str(len(urls) - 1) + '\x00'
        value = URL.sub(hide, value)
        value = BARE_URL.sub(hide, value)
        if pattern:
            value = pattern.sub(lambda m: aliases[m.group(0)] if entity_context(value, m.start(), m.end(), m.group(0), table['batch_id']) else m.group(0), value)
        if person_pattern:
            value = person_pattern.sub('〔人名〕', value)
        for label, rule in CONTACT_PATTERNS:
            value = re.sub(rule, '〔' + label + '〕', value)
        value = re.sub(r'\x00(\d+)\x00', lambda m: urls[int(m.group(1))], value)
        return value
    return text, domain


# --- 2026-10-28 release fix: street numbers, buildings and floors are masked
# to road / street level (after entity coding), plus three residual aliases.
CN='\u4e00-\u9fa5'
SEG=r'(?:[\u4e00-\u9fa5]{0,2}?段)'
ROAD=rf'(?:[{CN}A-Za-z0-9]{{1,12}}?(?:大道|路|大街|街|巷|道|沿街|里|村[一二三四五六七八九十\d]+组|组){SEG}?)'
NUM=r'(?:\d+(?:[-‑—]\d+)?号(?:院)?(?:附\d+号)?)'
BLD=rf'(?:[{CN}A-Za-z0-9 ]{{0,8}}?(?:大厦|中心|国际广场|国际|广场|芙蓉园|智汇园|金座|第一城|商场|百货|SOHO ?|时代\d+号|号楼))'
UNITC=r'(?:[A-Za-z]?\d*[A-Za-z\d一二三四五六七八九十]*[栋座幢]|\d+单元|[\d一二三四五六七八九十]+(?:层|楼|F)|附?[A-Za-z]?[\d‑-]{2,}(?:室|号)?|[A-Z]\d|\d+号楼|\d+号)'
TAIL=rf'(?:(?:〔[A-Z]\d\d-[^〕]+〕)?(?:{BLD})?(?:{UNITC})*)'
ADDR=re.compile(rf'({ROAD})({NUM})({TAIL})')
UNIT=re.compile(rf'(?:{UNITC})+')
PH='〔门牌已隐去〕'
BEFORE=re.compile(rf'(〔[A-Z]\d\d-E\d+-[a-z]〕|{PH}|大厦|中心|国际|广场|商场|百货|SOHO ?|第一城|[A-Z]区|园区?)$')
STRONG=re.compile(r'(?:[\d一二三四五六七八九十]+号(?:办公)?楼\s?\d{2,4}(?:层|楼|室)?(?:\d+号)?|\d+[栋幢]\d+单元(?:\d+[层楼])?(?:\d+号?)?|同栋楼\d+层\d+号)')
def mask_address(text,log=None):
    log=[] if log is None else log
    def a(m):
        road,num,tail=m.groups()
        if re.search(r'认字|文号',text[max(0,m.start()-8):m.start()+len(road)]): return m.group(0)
        codes=''.join(re.findall(r'〔[A-Z]\d\d-[^〕]+〕',tail))
        new=road+PH+codes; log.append((m.group(0),new)); return new
    text=ADDR.sub(a,text)
    def u(m):
        g=m.group(0)
        if not re.search(r'[栋座幢层楼F室单元]',g) : return g
        ctx=text[max(0,m.start()-12):m.start()]
        if BEFORE.search(ctx):
            log.append((ctx+'|'+g,PH)); return PH
        return g
    text=UNIT.sub(u,text)
    def st(m): log.append((m.group(0),PH)); return PH
    text=STRONG.sub(st,text)
    text=re.sub(re.escape(PH)+r'(?:[、，]\d+号)+',lambda m:(log.append((m.group(0),PH)),PH)[1],text)
    return re.sub(f'(?:{re.escape(PH)})+',PH,text)

LATE_ALIASES = {
    'B03': [('婚前 MV 双影像', '〔B03-E350-a〕'), ('婚前MV双影像', '〔B03-E350-b〕')],
}
LATE_TITLE_ALIASES = {
    'B02': [('Vendas e Cobrança', '〔B02-E609-a〕')],
}


def finish_text(value, batch_id, title=False):
    value = mask_address(value)
    for old, new in (LATE_TITLE_ALIASES if title else LATE_ALIASES).get(batch_id, []):
        value = value.replace(old, new)
    return value


def csv_bytes(rows, fieldnames):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=fieldnames, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode('utf-8')


def export(sources, tables, output):
    config = json.loads(Path(sources).read_text(encoding='utf-8'))
    output = Path(output)
    batches, roots, commitments = [], [], []
    for bid, meta in sorted(config['batches'].items()):
        table_path = Path(tables) / (bid + '.json')
        table = load_table(table_path)
        transform, domain = make_transform(table)
        questions, records = read_original(meta, bid)
        destination = output / 'data' / bid
        destination.mkdir(parents=True, exist_ok=True)
        for q in questions:
            q['question_text'] = transform(q['question_text'])
            q['是否点名题'] = str(q['是否点名题']).lower()
        (destination / 'questions.csv').write_bytes(csv_bytes(questions, ['question_id', '题型或分类', 'question_text', '是否点名题']))
        for row in records:
            row['answer_text'] = finish_text(transform(row['answer_text']), bid)
            row['sources'] = [{'order': s['order'], 'url': domain(s['url']), 'title': finish_text(transform(s['title']), bid, title=True) if s['title'] else transform(s['title']),
                               'kind': s['kind'], 'published_at': s['published_at']}
                              for s in row['sources']]
        (destination / 'answers.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in records), encoding='utf-8')
        if bid == 'B01':
            names = table['public_names']
            (destination / 'public-names.csv').write_bytes(csv_bytes(names, list(names[0])))
        grouped = {}
        for row in records:
            key = (row['platform'], row['question_id'])
            grouped[key] = grouped.get(key, 0) + 1
        summarize = lambda field: json.dumps({p: sorted({r[field] for r in records if r['platform'] == p}, key=str) for p in sorted({r['platform'] for r in records})}, ensure_ascii=False, separators=(',', ':'))
        repeats = sorted(set(grouped.values()))
        batches.append({'batch_id': bid, '公开名称': meta['name'],
                        '采样日期': ';'.join(sorted({r['sampled_at'][:10] for r in records if r['sampled_at']})),
                        '平台': ';'.join(sorted({r['platform'] for r in records})), '模型 ID': summarize('model'),
                        '题数': len(questions), '每题次数': ';'.join(map(str, repeats)),
                        '有效回答数': sum(r['status'] == 'valid' for r in records),
                        '失败数': sum(r['status'] != 'valid' for r in records),
                        '是否请求联网': summarize('web_search_requested'), '是否观察到联网调用': summarize('web_search_observed'),
                        'raw_root_sha256': meta['raw_root_sha256'], '是否在 2026-10-15 归档内': str(meta['archived']).lower()})
        roots.append({'batch_id': bid, 'raw_root_sha256': meta['raw_root_sha256'], 'scope': meta['root_scope'],
                      'manifest_file_mismatches': meta.get('manifest_file_mismatches'),
                      'manifest_raw_root_matches': meta.get('manifest_raw_root_matches')})
        commitments.append({'batch_id': bid, 'sha256': hashlib.sha256(table_path.read_bytes()).hexdigest()})
    (output / 'batches.csv').write_bytes(csv_bytes(batches, list(batches[0])))
    proofs = output / 'proofs'
    proofs.mkdir(exist_ok=True)
    (proofs / 'raw-roots.csv').write_bytes(csv_bytes(roots, list(roots[0])))
    (proofs / 'code-table-commitments.csv').write_bytes(csv_bytes(commitments, list(commitments[0])))
    return batches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--tables', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    for row in export(args.sources, args.tables, args.output):
        print(row['batch_id'], row['题数'], row['有效回答数'], row['失败数'])


if __name__ == '__main__':
    main()
