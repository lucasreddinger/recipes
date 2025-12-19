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
    text = text.replace("—", "---")   # em dash
    text = text.replace("–", "--")    # en dash
    # double quotes
    text = re.sub(r'"([^"]+)"', r"``\1''", text)
    # single quotes (not apostrophes)
    text = re.sub(r"(?<!\w)'(.*?)'(?!\w)", r"`\1'", text)
    return text

# --- entry point ---
if len(sys.argv) != 2:
    print("usage: python generate_recipes.py <input.yaml>")
    sys.exit(1)

input_yaml = sys.argv[1]
base = os.path.splitext(os.path.basename(input_yaml))[0]

with open(input_yaml, encoding="utf-8") as f:
    data = yaml.safe_load(f)

# format metadata
data["date"] = format_date(data.get("date", ""))
data["desc"] = typographic_latex(data.get("desc", "").rstrip("\n"))

# format ingredients and step descriptions
for step in data.get("steps", []):
    step["desc"] = typographic_latex(step.get("desc", "").rstrip("\n"))
    for item in step.get("items", []):
        item["amount"] = format_amount(item.get("amount", ""))
        item["desc"] = typographic_latex(item.get("desc", "").rstrip("\n"))

# jinja setup
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

