"""Word count of the manuscript body (problem .. significance), per section. Run: python paper/wordcount.py"""
import os
import re

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'manuscript.md')
text = open(path, encoding='utf-8').read()
body = text.split('## The problem')[1].split('## Software availability')[0]
count = lambda s: len(re.findall(r"[A-Za-z0-9'’\-]+", s))  # noqa: E731
print(f'{count(body):5d}  body total (target 2,000-2,100 incl. table; journal cap ~2,300 with headings and caption)')
for sec in re.split(r'\n## ', body):
    print(f'{count(sec):5d}  {sec.splitlines()[0][:50]}')
