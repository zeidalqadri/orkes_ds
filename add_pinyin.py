#!/usr/bin/env python3
"""Regenerate lyrics page with pinyin column - reconstructing from original HTML structure."""

import re

from bs4 import BeautifulSoup, NavigableString, Tag
from pypinyin import Style, pinyin

FILE = "/home/the_bomb/orkes_ds/lyrics/nopartyforcaodong_lyrics.html"

def has_chinese(text):
    return bool(re.search(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]', text))

def to_pinyin(text):
    """Convert Chinese text to pinyin with spaces."""
    if not has_chinese(text):
        return text
    result = []
    for ch in text:
        if re.match(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]', ch):
            py = pinyin(ch, style=Style.TONE)
            result.append(py[0][0] if py else ch)
        else:
            result.append(ch)
    return ' '.join(result)

with open(FILE) as f:
    content = f.read()
    soup = BeautifulSoup(content, 'html.parser')

count = 0
for grid in soup.select('.lyrics-grid'):
    cn_col = grid.find('div', class_='lyric-col cn')
    en_col = grid.find('div', class_='lyric-col en')
    if not cn_col or not en_col:
        continue
    if grid.find('div', class_='lyric-col py'):
        existing_py = grid.find('div', class_='lyric-col py')
        existing_py.decompose()

    py_col = soup.new_tag('div', **{'class': 'lyric-col py'})

    for child in cn_col.children:
        if isinstance(child, NavigableString):
            continue
        if not isinstance(child, Tag):
            continue

        tag_name = child.name
        classes = child.get('class', [])

        if 'section-tag' in classes:
            new = soup.new_tag(tag_name, **{'class': ' '.join(classes)})
            new.string = child.get_text()
            py_col.append(new)
        elif 'gap' in classes:
            new = soup.new_tag(tag_name, **{'class': 'gap'})
            py_col.append(new)
        elif 'line' in classes:
            text = child.get_text()
            new = soup.new_tag('span', **{'class': 'line'})
            if text.strip() and has_chinese(text):
                new.string = to_pinyin(text)
            elif text.strip():
                new.string = text
            else:
                new.string = ''
            py_col.append(new)
        else:
            new = soup.new_tag(tag_name)
            new.string = child.get_text()
            py_col.append(new)

    en_col.insert_before(py_col)
    count += 1

print(f"Updated {count} song grids with pinyin")

# Update CSS: 2-col to 3-col
for style_tag in soup.find_all('style'):
    if style_tag.string:
        old = style_tag.string
        # Only replace in the main lyrics grid rule outside media queries
        lines = old.split('\n')
        new_lines = []
        for line in lines:
            if 'grid-template-columns: 1fr 1fr;' in line and '@media' not in line:
                new_lines.append(line.replace('grid-template-columns: 1fr 1fr;', 'grid-template-columns: 1fr 1.2fr 1fr;'))
            else:
                new_lines.append(line)
        style_tag.string = '\n'.join(new_lines)

# Find the existing py styles or add them
py_css = '''
  .lyric-col.py {
    border-left: 1px solid var(--border);
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 0.85rem;
    color: #7a9a7a;
    line-height: 2.2;
    letter-spacing: 0;
    padding: 28px 20px;
  }
  .lyric-col.py .section-tag {
    display: inline-block;
    font-size: 0.6rem;
    letter-spacing: 3px;
    color: #3a6a3a;
    text-transform: uppercase;
    margin: 18px 0 4px;
    font-family: 'Crimson Text', 'Georgia', 'Times New Roman', serif !important;
  }
  .lyric-col.py .section-tag:first-child { margin-top: 0; }
  @media (max-width: 900px) {
    .lyrics-grid { grid-template-columns: 1fr 1fr; }
    .lyric-col.py { display: none; }
  }
  @media (max-width: 700px) {
    .lyrics-grid { grid-template-columns: 1fr; }
    .lyric-col.en { display: none; }
  }
'''

# Add py styles if not already present
all_style_text = ''
for style_tag in soup.find_all('style'):
    all_style_text += (style_tag.string or '')

if '.lyric-col.py' not in all_style_text:
    for style_tag in soup.find_all('style'):
        existing = style_tag.string or ''
        style_tag.string = existing + py_css
        break

with open(FILE, 'w') as f:
    f.write(str(soup))

print("Done — pinyin column added with proper spacing")
