import yaml
import sys
import os
from jinja2 import Environment, FileSystemLoader

if len(sys.argv) != 2:
    print("usage: python generate_recipes.py <input.yaml>")
    sys.exit(1)

input_yaml = sys.argv[1]
base = os.path.splitext(os.path.basename(input_yaml))[0]

with open(input_yaml, encoding="utf-8") as f:
    data = yaml.safe_load(f)

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

