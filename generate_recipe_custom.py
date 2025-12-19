import yaml
import sys
import os
import platform
import copy
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, date
import re

def format_date(d):
    fmt = '%-d~%B %Y' if platform.system() != 'Windows' else '%#d~%B %Y'
    if isinstance(d, (datetime, date)):
        return d.strftime(fmt)
    elif isinstance(d, str):
        try:
            return datetime.fromisoformat(d).strftime(fmt)
        except ValueError:
            return d.strip()
    return str(d).strip()

def latex_units(text):
    # turn "3 Tbsp" → "3~Tbsp", "10 oz" → "10~oz"
    return re.sub(r'(\d+|[\d–-]+)\s+([A-Za-z\.]+)', r'\1~\2', text)

def typographic(text):
    if not isinstance(text, str):
        return text

    # unicode dashes → latex dashes
    text = text.replace("—", "---").replace("–", "--")

    # markdown italics → \textit{}
    text = re.sub(r'\*([^\*]+)\*', r'\\textit{\1}', text)

    # smart quotes
    text = re.sub(r'"([^"]+)"', r"``\1''", text)
    text = re.sub(r"(?<!\w)'(.*?)'(?!\w)", r"`\1'", text)

    # units to nonbreaking spacing
    text = latex_units(text)

    return text.strip()

def quote_yaml_string(s):
    s = "" if s is None else str(s)
    return '"' + s.replace('"', '\\"') + '"'

if len(sys.argv) != 2:
    print("usage: python generate_recipe_custom.py <input.yaml>")
    sys.exit(1)

input_yaml = sys.argv[1]
base = os.path.splitext(os.path.basename(input_yaml))[0]

with open(input_yaml, encoding="utf-8") as f:
    data_raw = yaml.safe_load(f)

# keep raw ISO date for Hugo
raw_date = data_raw.get("date", "")

################################################################################
# TeX output (uses LaTeX typography)
################################################################################

data_tex = copy.deepcopy(data_raw)

data_tex["date"] = format_date(data_tex.get("date", ""))
data_tex["desc"] = typographic(data_tex.get("desc", ""))

for step in data_tex.get("steps", []):
    step["title"] = typographic(step.get("title", ""))
    step["desc"] = typographic(step.get("desc", ""))

for group in data_tex.get("groups", []):
    group["title"] = typographic(group.get("title", ""))
    group["items"] = [typographic(x) for x in group.get("items", [])]

env = Environment(
    loader=FileSystemLoader('.'),
    block_start_string='{%',
    block_end_string='%}',
    variable_start_string='{{',
    variable_end_string='}}',
    comment_start_string='[#',
    comment_end_string='#]',
    trim_blocks=True,
    lstrip_blocks=True
)

template = env.get_template("recipe_custom.tex.j2")
output_tex = template.render(**data_tex)

with open(f"{base}.tex", "w", encoding="utf-8") as f:
    f.write(output_tex)

################################################################################
# Markdown output for Hugo (no LaTeX, just Markdown / unicode)
################################################################################

md_lines = []

title = data_raw.get("title", "")
slug = data_raw.get("slug", "")
draft = data_raw.get("draft", False)
tags = data_raw.get("tags", [])
categories = data_raw.get("categories", [])

# front matter
md_lines.append("---")
md_lines.append(f'title: {quote_yaml_string(title)}')

if raw_date:
    md_lines.append(f"date: {raw_date}")

if slug:
    md_lines.append(f"slug: {quote_yaml_string(slug)}")

md_lines.append(f"draft: {'true' if draft else 'false'}")

if tags:
    md_lines.append("tags:")
    for t in tags:
        md_lines.append(f"  - {t}")

if categories:
    md_lines.append("categories:")
    for c in categories:
        md_lines.append(f"  - {c}")

md_lines.append("type: recipe")
md_lines.append("---")
md_lines.append("")

# description (raw markdown from YAML)
desc_md = (data_raw.get("desc", "") or "").strip()
if desc_md:
    md_lines.append(desc_md)
    md_lines.append("")

# ingredients
groups = data_raw.get("groups", [])
if groups:
    md_lines.append("## Ingredients")
    md_lines.append("")
    for g in groups:
        g_title = g.get("title", "")
        if g_title:
            md_lines.append(f"### {g_title}")
        for item in g.get("items", []) or []:
            md_lines.append(f"- {item}")
        md_lines.append("")

# steps
steps = data_raw.get("steps", [])
if steps:
    md_lines.append("## Steps")
    md_lines.append("")
    for step in steps:
        st_title = step.get("title", "")
        if st_title:
            md_lines.append(f"### {st_title}")
        step_desc = (step.get("desc", "") or "").strip()
        if step_desc:
            md_lines.append(step_desc)
        md_lines.append("")

with open(f"{base}.md", "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines))

print(f"wrote: {base}.tex")
print(f"wrote: {base}.md")

