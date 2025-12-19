import yaml
import sys
import os
import platform
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, date

# only replace common culinary fractions
def format_amount(val):
    fraction_map = {
        0.25: r"\nicefrac{1}{4}",
        0.5:  r"\nicefrac{1}{2}",
        0.75: r"\nicefrac{3}{4}",
        0.33: r"\nicefrac{1}{3}",
        0.66: r"\nicefrac{2}{3}",
        0.2:  r"\nicefrac{1}{5}",
        0.4:  r"\nicefrac{2}{5}",
        0.6:  r"\nicefrac{3}{5}",
        0.8:  r"\nicefrac{4}{5}",
    }
    if isinstance(val, float):
        return fraction_map.get(round(val, 2), str(val))
    return str(val)

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

if len(sys.argv) != 2:
    print("usage: python generate_recipes.py <input.yaml>")
    sys.exit(1)

input_yaml = sys.argv[1]
base = os.path.splitext(os.path.basename(input_yaml))[0]

with open(input_yaml, encoding="utf-8") as f:
    data = yaml.safe_load(f)

data["date"] = format_date(data.get("date", ""))
for step in data.get("steps", []):
    for item in step.get("items", []):
        item["amount"] = format_amount(item.get("amount", ""))

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

