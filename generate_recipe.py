import yaml
import sys
import os
import platform
import copy
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, date
import re

###############################################################################
# template filenames
###############################################################################
TEX_TEMPLATE_STEPS = "recipe_steps.tex.j2"
TEX_TEMPLATE_GROUPS = "recipe_groups.tex.j2"

###############################################################################
# helpers
###############################################################################

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
    if isinstance(val, int):
        return str(val)
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

def latex_units(text):
    # turn "3 Tbsp" → "3~Tbsp", "10 oz" → "10~oz"
    return re.sub(r'(\d+|[\d–-]+)\s+([A-Za-z\.]+)', r'\1~\2', text)

# apply LaTeX dash and quote typography
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

def norm(v):
    """coerce YAML scalar → clean string, safe for ints/floats/None"""
    if v is None:
        return ""
    return str(v).strip()

###############################################################################
# --- entry point ---
###############################################################################

if len(sys.argv) != 2:
    prog = os.path.basename(sys.argv[0])
    print(f"usage: python {prog} <input.yaml>")
    sys.exit(1)

input_yaml = sys.argv[1]
base = os.path.splitext(os.path.basename(input_yaml))[0]

with open(input_yaml, encoding="utf-8") as f:
    data_raw = yaml.safe_load(f)

# keep raw ISO date for Hugo
raw_date = data_raw.get("date", "")

steps = data_raw.get("steps", []) or []
groups = data_raw.get("groups", []) or []

# schema detection
has_step_items = any(isinstance(s.get("items"), list) and s.get("items") for s in steps)
has_groups = bool(groups)

if has_step_items and has_groups:
    style = "groups"   # prefer new style if both present
elif has_groups:
    style = "groups"
elif has_step_items:
    style = "steps"
else:
    style = "minimal"

################################################################################
# TeX output (uses LaTeX typography)
################################################################################

data_tex = copy.deepcopy(data_raw)

data_tex["date"] = format_date(data_tex.get("date", ""))
data_tex["desc"] = typographic(data_tex.get("desc", ""))

if style == "groups":
    # new style: groups + simple steps
    for step in data_tex.get("steps", []):
        step["title"] = typographic(step.get("title", ""))
        step["desc"] = typographic(step.get("desc", ""))

    # convert ingredient objects → formatted LaTeX strings
    for group in data_tex.get("groups", []):
        group["title"] = typographic(group.get("title", ""))
        rendered = []
        for it in group.get("items", []):
            raw_amt = it.get("amount")
            unit = norm(it.get("unit"))
            desc = typographic(norm(it.get("desc")))

            if isinstance(raw_amt, (int, float)):
                amt = format_amount(raw_amt)
            else:
                amt = norm(raw_amt)

            if amt and unit:
                txt = f"{amt} {unit} {desc}"
            elif amt:
                txt = f"{amt} {desc}"
            else:
                txt = desc

            txt = typographic(txt)
            rendered.append(txt)

        group["items"] = rendered

    tex_template_name = TEX_TEMPLATE_GROUPS

elif style == "steps":
    # old style: steps each have items[]
    for step in data_tex.get("steps", []):
        step["title"] = typographic(step.get("title", ""))
        step["desc"] = typographic(step.get("desc", ""))

        for item in step.get("items", []):
            raw_amt = item.get("amount")
            if isinstance(raw_amt, (int, float)):
                item["amount"] = format_amount(raw_amt)
            else:
                item["amount"] = norm(raw_amt)
            item["desc"] = typographic(norm(item.get("desc")))

    tex_template_name = TEX_TEMPLATE_STEPS

else:
    # minimal: no groups, no step-items, just titles + desc
    for step in data_tex.get("steps", []):
        step["title"] = typographic(step.get("title", ""))
        step["desc"] = typographic(step.get("desc", ""))
    tex_template_name = TEX_TEMPLATE_STEPS

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

template = env.get_template(tex_template_name)
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

if style == "groups":
    # ingredients
    if groups:
        md_lines.append("## Ingredients")
        md_lines.append("")
        for g in groups:
            g_title = g.get("title", "")
            if g_title:
                md_lines.append(f"### {g_title}")
            for it in g.get("items", []):
                raw_amt = it.get("amount")
                unit = norm(it.get("unit"))
                desc = norm(it.get("desc"))

                if isinstance(raw_amt, (int, float)):
                    amt = str(raw_amt)
                else:
                    amt = norm(raw_amt)

                if amt and unit:
                    line = f"- {amt} {unit} {desc}"
                elif amt:
                    line = f"- {amt} {desc}"
                else:
                    line = f"- {desc}"

                md_lines.append(line)
            md_lines.append("")

    # steps
    if steps:
        md_lines.append("## Steps")
        md_lines.append("")
        for step in steps:
            st_title = (step.get("title", "") or "").strip()
            if st_title:
                md_lines.append(f"### {st_title}")
            step_desc = (step.get("desc", "") or "").strip()
            if step_desc:
                md_lines.append(step_desc)
            md_lines.append("")

else:
    # steps (old style or minimal)
    if steps:
        md_lines.append("## Steps")
        md_lines.append("")
        for step in steps:
            st_title = (step.get("title", "") or "").strip()
            if st_title:
                md_lines.append(f"### {st_title}")
            step_desc = (step.get("desc", "") or "").strip()
            if step_desc:
                md_lines.append(step_desc)
            md_lines.append("")

            if style == "steps":
                items = step.get("items", []) or []
                for it in items:
                    raw_amt = it.get("amount")
                    unit = norm(it.get("unit"))
                    desc = norm(it.get("desc"))

                    if isinstance(raw_amt, (int, float)):
                        amt = str(raw_amt)
                    else:
                        amt = norm(raw_amt)

                    nice = " ".join(x for x in [amt, unit, desc] if x).strip()
                    if nice:
                        md_lines.append(f"- {nice}")
                md_lines.append("")

with open(f"{base}.md", "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines))

print(f"wrote: {base}.tex")
print(f"wrote: {base}.md")

