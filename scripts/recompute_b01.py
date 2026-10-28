#!/usr/bin/env python3
"""Recompute frozen B01 counters using public files only; report all differences."""
import argparse
import csv
import json
from pathlib import Path
import re

GROUPS = [('全城代表',1,3),('新房',4,6),('改善',7,9),('高端改善',10,12),
          ('豪宅',13,15),('刚改',16,18),('高新区',19,21),('天府新区',22,24),
          ('城南',25,27),('主城区',28,30),('大平层',31,33),('低密洋房',34,36),
          ('通勤',37,39),('品质',40,42),('家庭',43,45),('总括',46,50)]
LINK = re.compile(r'\[[^\]]*\]\(https?://[^)]+\)')


def recompute(root):
    folder = Path(root) / 'data' / 'B01'
    names = list(csv.DictReader((folder / 'public-names.csv').open(encoding='utf-8', newline='')))
    records = [json.loads(line) for line in (folder / 'answers.jsonl').read_text(encoding='utf-8').splitlines()]
    themes = {label: {f'Q{n:02d}' for n in range(first, last + 1)} for label, first, last in GROUPS}
    broad = themes['全城代表'] | themes['总括']
    bodies = [(r['question_id'], LINK.sub('', r['answer_text'])) for r in records]
    summary, article, items = [], [], []
    def add(target, label, actual, expected):
        row = {'check': label, 'actual': actual, 'expected': expected, 'match': actual == expected}
        target.append(row)
        return row
    add(article, 'broad_questions', len(broad), 8)
    add(article, 'broad_answers', sum(q in broad for q, _ in bodies), 40)
    add(article, 'theme_count', len(themes), 16)
    for row in names:
        eid = row['代号']
        codes = set(json.loads(row['article_codes']))
        hits = [(q, any(code in body for code in codes)) for q, body in bodies]
        count = lambda qids: sum(hit and q in qids for q, hit in hits)
        metrics = {'broad': count(broad), 'all': sum(hit for _, hit in hits),
                   'theme_breadth': sum(count(qids) > 0 for qids in themes.values()),
                   'stable_questions_5_of_5': sum(count({f'Q{n:02d}'}) == 5 for n in range(1,51))}
        for metric, value in metrics.items():
            add(summary, eid + '/' + metric, value, int(row[metric + '_expected']))
        for metric, expected in json.loads(row['article_checks']):
            if metric in metrics:
                actual = metrics[metric]
            elif metric in themes:
                actual = count(themes[metric])
            else:
                actual = count({metric})
            add(article, eid + '/' + metric, actual, expected)
        items.append({'entity': eid, 'metrics': metrics})
    compact = lambda rows: {'一致': sum(x['match'] for x in rows), '不一致': sum(not x['match'] for x in rows),
                            'differences': [x for x in rows if not x['match']]}
    return {'method': 'remove Markdown links; exact published variant codes; once per answer',
            'project_counts': compact(summary), 'article_numbers': compact(article),
            'checks': {'project_counts': summary, 'article_numbers': article}, 'results': items}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = recompute(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(int(any(result[k]['不一致'] for k in ['project_counts','article_numbers'])))


if __name__ == '__main__':
    main()
