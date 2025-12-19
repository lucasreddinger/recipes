import yaml
import sys
import os
import platform
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

if len(sys.argv) != 2:
    print("usage: python generate_recipe_custom.py <input.yaml>")
    sys.exit(1)

input_yaml = sys.argv[1]
base = os.path.splitext(os.path.basename(input_yaml))[0]

with open(input_yaml, encoding="utf-8") as f:
    data = yaml.safe_load(f)

data["date"] = format_date(data.get("date", ""))
data["desc"] = typographic(data.get("desc", ""))

for step in data.get("steps", []):
    step["title"] = typographic(step.get("title", ""))
    step["desc"] = typographic(step.get("desc", ""))

for group in data.get("groups", []):
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
output = template.render(**data)

with open(f"{base}.tex", "w", encoding="utf-8") as f:
    f.write(output)

print(f"wrote: {base}.tex")

