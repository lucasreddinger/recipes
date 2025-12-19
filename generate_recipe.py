import yaml
import sys
import os
import platform
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, date
import re

# only format common culinary fractions; others stay as decimals
def format_amount(val):
    fraction_map = {
        0.25: r"\nicefrac{1}{4}",
        0.5:  r"\nicefrac{1}{2}",
        0.75: r"\nicefrac{3}{4}",
        0.33: r"\nicefrac{1}{3}",
        0.66: r"\nicefrac{2}{3}",
    }
    if isinstance(val, float):
        return fraction_map.get(round(val, 2), str(val))
    return str(val)

# convert ISO or date object to LaTeX-style date (e.g. 18~December 2025)
def format_date(d):
    fmt = '%-d~%B %Y' if platform.system() != 'Windows' else '%#d~%B %Y'
    if isinstance(d, (datetime, date)):
        return d.strftime(fmt)
    elif isinstance(d, str):
        try:
            parsed = datetime.fromisoformat(d)
            return parsed.strftime(fmt)
        except ValueError:
            return d.strip()
    return str(d).strip()

# apply LaTeX dash and quote typography
def typographic_latex(text):
    if not isinstance(text, str):
        return text
    # unicode dashes to LaTeX
    text = text.replace("—", "---")
    text = text.replace("–", "--")
    # double quotes
    text = re.sub(r'"([^"]+)"', r"``\1''", text)
    # single quotes (not apostrophes)
    text = re.sub(r"(?<!\w)'(.*?)'(?!\w)", r"`\1'", text)
    return text

def quote_yaml_string(s):
    s = "" if s is None else str(s)
    return '"' + s.replace('"', '\\"') + '"'

# --- entry point ---
if len(sys.argv) != 2:
    print("usage: python generate_recipes.py <input.yaml>")
    sys.exit(1)

input_yaml = sys.argv[1]
base = os.path.splitext(os.path.basename(input_yaml))[0]

with open(input_yaml, encoding="utf-8") as f:
    data = yaml.safe_load(f)

################################################################################
# TeX output (LaTeX formatting stays)
################################################################################

data["date"] = format_date(data.get("date", ""))
data["desc"] = typographic_latex(data.get("desc", "").rstrip("\n"))

for step in data.get("steps", []):
    step["desc"] = typographic_latex(step.get("desc", "").rstrip("\n"))
    for item in step.get("items", []):
        item["amount"] = format_amount(item.get("amount", ""))
        item["desc"] = typographic_latex(item.get("desc", "").rstrip("\n"))

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

template = env.get_template("recipe_template.tex.j2")
output = template.render(**data)

with open(f"{base}.tex", "w", encoding="utf-8") as f:
    f.write(output)

print(f"wrote: {base}.tex")

################################################################################
# Markdown output for Hugo (no LaTeX)
################################################################################

md_lines = []

title = data.get("title", "")
slug = data.get("slug", "")
raw_date = data.get("date", "")
draft = data.get("draft", False)
tags = data.get("tags", [])
categories = data.get("categories", [])

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

# desc
desc_md = (data.get("desc", "") or "").strip()
if desc_md:
    md_lines.append(desc_md)
    md_lines.append("")

# Steps
steps = data.get("steps", [])
if steps:
    md_lines.append("## Steps")
    md_lines.append("")
    for step in steps:
        title = (step.get("title", "") or "").strip()
        if title:
            md_lines.append(f"### {title}")

        step_desc = (step.get("desc", "") or "").strip()
        if step_desc:
            md_lines.append(step_desc)

        md_lines.append("")

        items = step.get("items", []) or []
        for it in items:
            amt = it.get("amount", "")
            unit = it.get("unit", "")
            desc = it.get("desc", "")
            nice = " ".join(x for x in [str(amt), unit, desc] if x).strip()
            if nice:
                md_lines.append(f"- {nice}")
        md_lines.append("")

with open(f"{base}.md", "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines))

print(f"wrote: {base}.md")

