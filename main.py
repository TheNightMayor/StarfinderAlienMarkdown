# TODO
# Fix replacement skill - Know.
# CSV gen
# Fix reddit people's assertion error
# Add utils to generate unique_leaves, counts, and lookup for a sub-dict of d in interactive mode


#####################
# CONFIG
#####################


from fractions import Fraction
import os
from copy import deepcopy
from tqdm import tqdm
import traceback
import sys
import json
import regex as re
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup, NavigableString

import inspect
import logging
import linecache



#####################
# PROGRAM
#####################


sizes = ['Fine', 'Diminutive', 'Tiny', 'Small', 'Medium', 'Large', 'Huge', 'Gargantuan', 'Colossal']

def parseInt(s, stringIfFail=False):
    def _parseInt(s):
        return int(s.strip().replace(",", "").replace("+ ", "+").replace("- ", "-"))

    if stringIfFail:
        try:
            return _parseInt(s)
        except:
            return s.strip()
    else:
        return _parseInt(s)


def parsePage(html, url):
    pageObject = {}

    html = re.sub(r'<\s*/?\s*br\s*/?\s*>', '<br/>', html)
    html = re.sub(r'[−—–‐‑‒―]|&ndash;|&mdash;', "-", html)
    html = re.sub(r'’', "'", html)

    soup = BeautifulSoup(html, "html.parser")
    e = soup.select_one("div#main table tr td span")
    if e is None:
        raise ValueError("Unable to find the main alien block for " + url)

    title1 = None
    for title_tag in e.find_all("h1", class_="title"):
        if title_tag.find("a"):
            title1 = title_tag
            break
    if title1 is None:
        title1 = e.find("h1", class_="title")

    title1_text = title1.get_text(strip=True) if title1 else None
    pageObject["title1"] = title1_text
    pageObject["family"] = None
    pageObject["array"] = None
    icon_texts = []
    for title_tag in e.find_all("h1", class_="title"):
        for img in title_tag.find_all("img"):
            text = img.get("alt") or img.get("title")
            if text:
                icon_texts.append(text.strip())
        if icon_texts:
            break
    if icon_texts:
        pageObject["array"] = icon_texts

    def _normalize_family_label(family):
        family = family.strip()
        if family.lower().endswith("s") and not family.lower().endswith(("ss", "us", "is", "as")):
            return family[:-1]
        return family

    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)
    family_values = query.get("Family") or query.get("family")
    if family_values:
        family = family_values[0].strip()
        if family and family.lower() != "none":
            pageObject["family"] = _normalize_family_label(family)
    pageObject["source"] = None
    source_tag = e.find("b", string="Source")
    if source_tag:
        link = source_tag.find_next_sibling("a")
        if link:
            pageObject["source"] = link.get_text(strip=True)

    title2 = e.find("h2", class_="title")
    if title2:
        title2_text = title2.get_text(strip=True)
        result = re.search(r'^(.*?) CR ([0-9/]+)(?:/MR (\d+))?$', title2_text)
        if result:
            pageObject["title1"] = result.group(1).strip() or pageObject.get("title1")
            cr_value = result.group(2)
            pageObject["CR"] = float(Fraction(cr_value)) if "/" in cr_value else parseInt(cr_value, stringIfFail=True)

    def _family_first_title(title, family):
        if not title or not family:
            return title
        family = family.strip()
        title = title.strip()
        if not family or not title:
            return title
        family_regex = re.compile(rf'\b{re.escape(family)}\b', re.I)
        variant = family_regex.sub('', title).strip()
        variant = re.sub(r'[\s,]+', ' ', variant).strip()
        if not variant:
            return family
        return f"{family} {variant}"

    if pageObject.get("family") and pageObject.get("title1"):
        pageObject["title1"] = _family_first_title(pageObject["title1"], pageObject["family"])

    def _text_before_header(node):
        if isinstance(node, NavigableString):
            return str(node), False
        if getattr(node, "name", None) == "br":
            return "\n", False
        if getattr(node, "name", None) in ["h2", "h3"] and "framing" in (node.get("class") or []):
            return "", True
        result = []
        for child in node.contents:
            text, stop = _text_before_header(child)
            result.append(text)
            if stop:
                return "".join(result), True
        return "".join(result), False

    def _collect_until_header(header_name):
        header = e.find("h3", class_="framing", string=header_name)
        if not header:
            return None
        result = []
        node = header.next_sibling
        while node is not None:
            if getattr(node, "name", None) in ["h2", "h3"] and "framing" in (node.get("class") or []):
                break
            if isinstance(node, NavigableString):
                result.append(str(node))
            elif getattr(node, "name", None) == "br":
                result.append("\n")
            else:
                text, stop = _text_before_header(node)
                result.append(text)
                if stop:
                    break
            node = node.next_sibling
        return "".join(result).strip()

    def _collect_summary():
        if title2 is None:
            return ""
        node = title2.next_sibling
        result = []
        while node is not None and not (
            getattr(node, "name", None) in ["h2", "h3"] and
            "framing" in (node.get("class") or [])
        ):
            if isinstance(node, NavigableString):
                result.append(str(node))
            elif getattr(node, "name", None) == "br":
                result.append("\n")
            else:
                result.append(node.get_text())
            node = node.next_sibling
        return "".join(result).strip()

    summary_text = _collect_summary()
    if summary_text:
        xp_match = re.search(r'XP\s+([\d,]+)', summary_text)
        if xp_match:
            pageObject["XP"] = parseInt(xp_match.group(1))

        init_match = re.search(r'Init\s+([+-]?\d+)', summary_text)
        if init_match:
            pageObject["initiative"] = {"bonus": parseInt(init_match.group(1))}

        senses_match = re.search(r'Senses\s+(.+?)(?:;|$)', summary_text)
        if senses_match:
            pageObject["senses"] = senses_match.group(1).strip()

        perception_match = re.search(r'Perception\s+([+-]?\d+)', summary_text)
        if perception_match:
            pageObject["perception"] = parseInt(perception_match.group(1))

        aura_match = re.search(r'Aura\s+(.+?)(?:;|$)', summary_text, re.I)
        if aura_match:
            pageObject["aura"] = aura_match.group(1).strip()

        reach_match = re.search(r'Reach\s+(.+?)(?:;|$)', summary_text)
        if reach_match:
            pageObject["reach"] = reach_match.group(1).strip()

        def _parse_species_class_line(line):
            gender_terms = ["Genderless", "Male", "Female", "Neuter", "Agender", "Nonbinary", "Non-binary", "Unknown"]
            trimmed = line.strip()
            for gender in gender_terms:
                if trimmed.lower().startswith(gender.lower() + " "):
                    trimmed = trimmed[len(gender):].strip()
                    break
            if not trimmed:
                return
            # species is usually capitalized or acronym, class is usually lowercase
            parts = trimmed.split()
            if len(parts) < 2:
                return
            if parts[-1].islower() and not re.search(r'\b(' + '|'.join(sizes).lower() + r')\b', trimmed.lower()):
                pageObject["species"] = " ".join(parts[:-1])
                pageObject["class"] = parts[-1]

        for line in [ln.strip() for ln in summary_text.splitlines() if ln.strip()]:
            if any(line.startswith(prefix) for prefix in ["XP", "Init", "Senses", "Perception"]):
                continue
            sizes_regex = '|'.join(sizes)
            result = re.search(r'^(.+?)\s+(' + sizes_regex + r')\s+(.+?)(?:\s*\((.+)\))?$', line)
            if result:
                pageObject["alignment"] = {"raw": result.group(1), "cleaned": result.group(1).replace("Always ", "")}
                pageObject["size"] = result.group(2)
                pageObject["type"] = result.group(3)
                if result.group(4):
                    pageObject["subtypes"] = [x.strip() for x in result.group(4).split(",")]
                break
            _parse_species_class_line(line)

    def _split_fields(text):
        return [item.strip() for item in re.split(r';\s*(?![^()]*\))', text) if item.strip()]

    defense_text = _collect_until_header("Defense")
    if defense_text:
        pageObject["defense"] = {}
        for line in [ln.strip() for ln in defense_text.splitlines() if ln.strip()]:
            if line.startswith("HP"):
                hp_match = re.search(r'HP\s*([0-9,]+)', line)
                if hp_match:
                    pageObject["defense"]["HP"] = parseInt(hp_match.group(1))
                else:
                    pageObject["defense"]["HP"] = line.split("HP", 1)[1].strip()
            elif line.startswith("EAC") or line.startswith("KAC"):
                for part in _split_fields(line):
                    result = re.search(r'^(EAC|KAC)\s+([+-]?\d+)', part)
                    if result:
                        pageObject["defense"][result.group(1)] = parseInt(result.group(2))
            elif any(line.startswith(x) for x in ["Fort", "Ref", "Will"]):
                for part in _split_fields(line):
                    result = re.search(r'^(Fort|Ref|Will)\s+([+-]?\d+)', part)
                    if result:
                        pageObject["defense"][result.group(1).lower()] = parseInt(result.group(2))
                    else:
                        stripped = part.strip()
                        if stripped:
                            pageObject["defense"].setdefault("save_modifiers", []).append(stripped)
            elif line.startswith("Defensive Abilities"):
                pageObject["defense"]["defensive_abilities"] = line[len("Defensive Abilities"):].strip()
            elif line.startswith("DR"):
                for part in _split_fields(line):
                    if part.startswith("DR"):
                        pageObject["defense"]["DR"] = part[len("DR"):].strip()
                    elif part.startswith("Immunities"):
                        pageObject["defense"]["immunities"] = part[len("Immunities"):].strip()
                    elif part.startswith("Resistances"):
                        pageObject["defense"]["resistances"] = part[len("Resistances"):].strip()
                    elif part.startswith("SR"):
                        pageObject["defense"]["SR"] = parseInt(part[len("SR"):].strip())

    offense_text = _collect_until_header("Offense")
    if offense_text:
        pageObject["offense"] = {}
        normalized = offense_text.strip()
        match = re.search(r'Speed\s+(.+?)(?=(?:Reach|Melee|Ranged|Offensive Abilities|Spell-Like Abilities|Spells|$))', normalized)
        if match:
            pageObject["offense"]["speed"] = match.group(1).strip()
        match = re.search(r'Melee\s+(.+?)(?=(?:Ranged|Offensive Abilities|Spell-Like Abilities|Spells|$))', normalized)
        if match:
            pageObject["offense"]["melee"] = match.group(1).strip()
        match = re.search(r'Ranged\s+(.+?)(?=(?:Melee|Offensive Abilities|Spell-Like Abilities|Spells|$))', normalized)
        if match:
            pageObject["offense"]["ranged"] = match.group(1).strip()
        match = re.search(r'Offensive Abilities\s+(.+?)(?=(?:Spell-Like Abilities|Spells|$))', normalized)
        if match:
            pageObject["offense"]["offensive_abilities"] = match.group(1).strip()

        def _split_spell_heading(line, regex):
            heading_match = re.search(regex, line, re.I)
            if not heading_match:
                return None, None
            heading = heading_match.group(1).strip()
            remainder = line[heading_match.end():].strip()
            return heading, remainder

        spell_sections = []
        for line in [ln.strip() for ln in offense_text.splitlines() if ln.strip()]:
            if re.search(r'\bSpell-Like Abilities\b', line, re.I):
                heading, remainder = _split_spell_heading(line, r'(Spell-Like Abilities(?:\s*\([^)]*\))?)')
                if heading:
                    spell_sections.append({"title": heading, "items": []})
                    if remainder:
                        spell_sections[-1]["items"].append(remainder)
                    continue
            if re.search(r'\bSpells?(?:\s+(?:Known|Prepared|Readied))?\b', line, re.I) and not re.search(r'\bSpell-Like Abilities\b', line, re.I):
                heading, remainder = _split_spell_heading(line, r'((?:\w+\s+)?Spells?(?:\s+(?:Known|Prepared|Readied))?(?:\s*\([^)]*\))?)')
                if heading:
                    spell_sections.append({"title": heading, "items": []})
                    if remainder:
                        spell_sections[-1]["items"].append(remainder)
                    continue
            if spell_sections:
                spell_sections[-1]["items"].append(line)

        if spell_sections:
            pageObject["offense"]["spells"] = spell_sections

        reach_match = re.search(r'Reach\s+(.+?)(?=(?:;|Melee|Ranged|Offensive Abilities|Spell-Like Abilities|Spells|$))', normalized)
        if reach_match:
            pageObject["reach"] = reach_match.group(1).strip()

    statistics_text = _collect_until_header("Statistics")
    if statistics_text:
        pageObject["statistics"] = {}
        result = re.search(r'STR\s+([+-]?\d+|[—-]);\s*DEX\s+([+-]?\d+|[—-]);\s*CON\s+([+-]?\d+|[—-]);\s*INT\s+([+-]?\d+|[—-]);\s*WIS\s+([+-]?\d+|[—-]);\s*CHA\s+([+-]?\d+|[—-])', statistics_text)
        if result:
            pageObject["statistics"]["ability_scores"] = {
                k: (None if v.strip() in ["-", "—"] else int(v))
                for k, v in zip(["STR", "DEX", "CON", "INT", "WIS", "CHA"], result.groups())
            }
        result = re.search(r'Feats\s+([\s\S]+?)(?=(?:Skills|Languages|Other Abilities|$))', statistics_text)
        if result:
            pageObject["statistics"]["feats"] = result.group(1).strip()
        result = re.search(r'Skills\s+([\s\S]+?)(?=(?:Languages|Other Abilities|$))', statistics_text)
        if result:
            pageObject["statistics"]["skills"] = result.group(1).strip()
        result = re.search(r'Languages\s+([\s\S]+?)(?=(?:Gear|Other Abilities|$))', statistics_text)
        if result:
            pageObject["statistics"]["languages"] = result.group(1).strip()
        result = re.search(r'Gear\s+([\s\S]+?)(?=(?:Augmentations|Other Abilities|$))', statistics_text)
        if result:
            pageObject["statistics"]["gear"] = result.group(1).strip()
        result = re.search(r'Other Abilities\s+([\s\S]+?)(?=(?:Gear|$))', statistics_text)
        if result:
            pageObject["statistics"]["other_abilities"] = result.group(1).strip()

    ecology_text = _collect_until_header("Ecology")
    if ecology_text:
        pageObject["ecology"] = {}
        result = re.search(r'Environment\s+(.+?)(?=(?:Organization|$))', ecology_text)
        if result:
            pageObject["ecology"]["environment"] = result.group(1).strip()
        result = re.search(r'Organization\s+(.+)', ecology_text)
        if result:
            pageObject["ecology"]["organization"] = result.group(1).strip()

    def _text_with_spacing(node):
        if isinstance(node, NavigableString):
            return str(node)
        if getattr(node, "name", None) == "br":
            return "\n"
        return node.get_text(" ", strip=True)

    special_section = e.find("h3", class_="framing", string="Special Abilities")
    if special_section:
        pageObject["special_abilities"] = {}
        node = special_section.next_sibling
        current = None
        buffer = []
        while node is not None and not (
            getattr(node, "name", None) in ["h2", "h3"]
        ):
            if getattr(node, "name", None) == "b":
                if current:
                    pageObject["special_abilities"][current] = " ".join(buffer).strip()
                    buffer = []
                current = node.get_text(strip=True)
            else:
                buffer.append(_text_with_spacing(node))
            node = node.next_sibling
        if current:
            pageObject["special_abilities"][current] = " ".join(buffer).strip()

    description_header = e.find("h2", class_="title", string="Description")
    if description_header:
        node = description_header.next_sibling
        desc_parts = []
        while node is not None:
            if isinstance(node, NavigableString):
                desc_parts.append(str(node))
            elif getattr(node, "name", None) == "br":
                desc_parts.append("\n")
            else:
                desc_parts.append(node.get_text())
            node = node.next_sibling
        pageObject["desc_long"] = "".join(desc_parts).strip()
    else:
        title1 = e.find("h1", class_="title")
        if title1:
            node = title1.next_sibling
        else:
            node = None
        desc_parts = []
        while node is not None and not (
            getattr(node, "name", None) == "h1" and
            "title" in (node.get("class") or [])
        ):
            if getattr(node, "name", None) == "b" and node.get_text(strip=True) == "Source":
                while node is not None and getattr(node, "name", None) != "br":
                    node = node.next_sibling
                if getattr(node, "name", None) == "br":
                    node = node.next_sibling
                continue
            if isinstance(node, NavigableString):
                desc_parts.append(str(node))
            elif getattr(node, "name", None) == "br":
                desc_parts.append("\n")
            else:
                desc_parts.append(node.get_text())
            node = node.next_sibling
        desc_text = "".join(desc_parts).strip()
        if desc_text:
            pageObject["desc_long"] = desc_text

    return pageObject


def yaml_quote(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    value = str(value)
    if "\n" in value:
        value = " ".join(line.strip() for line in value.splitlines() if line.strip())
    if value == "" or re.search(r'^[\s+]|[:{}\[\],&*#?\-|<>=!%@\\"\']', value):
        return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return value


def yaml_list(name, items, key_name=None):
    if not items:
        return []
    lines = [f"{name}:"]
    for item in items:
        if isinstance(item, dict):
            if key_name and key_name in item:
                lines.append(f"  - {key_name}: {yaml_quote(item[key_name])}")
                for k, v in item.items():
                    if k == key_name:
                        continue
                    lines.append(f"    {k}: {yaml_quote(v)}")
            else:
                lines.append("  -")
                for k, v in item.items():
                    lines.append(f"    {k}: {yaml_quote(v)}")
        else:
            if name == "Spells" and ": " in item:
                key, value = item.split(": ", 1)
                quoted_value = '"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'
                lines.append(f"  - {key}: {quoted_value}")
            else:
                lines.append(f"  - {yaml_quote(item)}")
    return lines


def render_markdown(pageObject):
    def parse_skill_list(skills_text):
        if not skills_text:
            return []
        entries = [x.strip() for x in re.split(r',\s*(?![^()]*\))', skills_text) if x.strip()]
        out = []
        for entry in entries:
            entry = re.sub(r'\s*:\s*(?:""|\'\')\s*$', '', entry).strip()
            m = re.match(r'^(.+?)\s+([+-]?\d+(?:\s*\([^)]*\))?)$', entry)
            if m:
                out.append({"name": m.group(1).strip(), "desc": m.group(2).strip()})
            else:
                out.append({"name": entry, "desc": ""})
        return out

    def yaml_quote_skill_desc(value):
        if value is None:
            return "null"
        value = str(value)
        if "(" in value and ")" in value:
            return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'
        return value

    def parse_defensive_abilities(defensive_text):
        if not defensive_text:
            return []
        parts = [x.strip() for x in re.split(r';\s*(?![^()]*\))', defensive_text) if x.strip()]
        out = []
        for part in parts:
            match = re.match(r'^(DR|Resistances|Immunities|Weaknesses)\s*(.*)$', part, re.IGNORECASE)
            if match:
                label = match.group(1)
                desc = match.group(2).strip()
                name = label.upper() if label.lower() == 'dr' else label.title()
                out.append({"name": name, "desc": desc})
            else:
                out.append({"name": "Defensive Abilities", "desc": part})
        return out

    def parse_special_abilities(specials):
        if not specials:
            return []
        out = []
        for name, desc in specials.items():
            out.append({"name": name, "desc": desc})
        return out

    def parse_defensive_entries(defense):
        out = []
        if not defense:
            return out
        if defense.get("defensive_abilities"):
            out.extend(parse_defensive_abilities(defense.get("defensive_abilities")))
        if defense.get("DR"):
            out.append({"name": "DR", "desc": defense.get("DR")})
        if defense.get("immunities"):
            out.append({"name": "Immunities", "desc": defense.get("immunities")})
        if defense.get("resistances"):
            out.append({"name": "Resistances", "desc": defense.get("resistances")})
        if defense.get("SR") is not None:
            out.append({"name": "SR", "desc": defense.get("SR")})
        return out

    def format_spell_sections(sections):
        out = []
        if not sections:
            return out
        for section in sections:
            title = section.get("title", "").strip()
            if title:
                m = re.match(r'(.+?)(\s*\([^)]*\))?$', title)
                if m:
                    heading = f"**{m.group(1).strip()}**" + (m.group(2) or "")
                else:
                    heading = f"**{title}**"
                out.append(heading)
            for item in section.get("items", []):
                if not item:
                    continue
                pieces = re.split(
                    r'(?=(?:At will|[0-9]+(?:st|nd|rd|th)?\s*\([^)]*\)|[0-9]+/(?:day|rounds?|week|weeks?))\s*[:—–-])',
                    item,
                    flags=re.I,
                )
                for piece in pieces:
                    piece = piece.strip()
                    if not piece:
                        continue
                    normalized_piece = re.sub(
                        r'(?i)\b(At will|[0-9]+(?:st|nd|rd|th)?\s*\([^)]*\)|[0-9]+/(?:day|rounds?|week|weeks?))\s*[—–-]\s*',
                        r'\1: ',
                        piece,
                    )
                    out.append(normalized_piece.strip())
        return out

    lines = ["---"]
    def add_field(key, value):
        if value is None:
            return
        if isinstance(value, list):
            lines.extend(yaml_list(key, value))
            return
        if key == "Gear":
            gear_value = str(value).replace("\n", " ").strip()
            quoted = '"' + gear_value.replace('\\', '\\\\').replace('"', '\\"') + '"'
            lines.append(f"{key}: {quoted}")
            return
        lines.append(f"{key}: {yaml_quote(value)}")

    add_field("name", pageObject.get("title1"))
    add_field("family", pageObject.get("family"))
    add_field("array", pageObject.get("array"))
    add_field("species", pageObject.get("species"))
    add_field("class", pageObject.get("class"))
    add_field("cr", pageObject.get("CR"))
    xp = pageObject.get("XP")
    if xp is not None:
        add_field("XP", f"{int(xp):,}")
    defense = pageObject.get("defense", {})
    add_field("hp", defense.get("HP"))
    add_field("alignment", pageObject.get("alignment", {}).get("cleaned") if pageObject.get("alignment") else None)
    add_field("size", pageObject.get("size"))
    add_field("type", pageObject.get("type"))
    if pageObject.get("subtypes"):
        subtypes = pageObject.get("subtypes")
        if isinstance(subtypes, list):
            add_field("subtype", f"({', '.join(subtypes)})")
        else:
            add_field("subtype", subtypes)
    if defense.get("EAC") is not None or defense.get("KAC") is not None:
        ac_parts = []
        if defense.get("EAC") is not None:
            ac_parts.append(f"EAC: {defense['EAC']}")
            add_field("EAC", defense.get("EAC"))
        if defense.get("KAC") is not None:
            ac_parts.append(f"KAC: {defense['KAC']}")
            add_field("KAC", defense.get("KAC"))
        add_field("ac", " ".join(ac_parts))
    if pageObject.get("initiative"):
        init_value = pageObject["initiative"].get("bonus")
        add_field("Init", init_value)
        add_field("modifier", init_value)
    add_field("Speed", pageObject.get("offense", {}).get("speed"))
    add_field("Reach", pageObject.get("reach"))
    add_field("Aura", pageObject.get("aura"))
    ability_scores = pageObject.get("statistics", {}).get("ability_scores")
    if ability_scores:
        lines.append("abilitymods:")
        for k, v in ability_scores.items():
            lines.append(f"  - {k}: {yaml_quote(v if v is not None else '—')}")
    skills = parse_skill_list(pageObject.get("statistics", {}).get("skills", ""))
    if skills:
        lines.append("Skills:")
        for skill in skills:
            lines.append(f"  - {skill['name']}: {yaml_quote_skill_desc(skill['desc'])}")
    add_field("feats", pageObject.get("statistics", {}).get("feats"))
    add_field("Languages", pageObject.get("statistics", {}).get("languages"))
    add_field("Gear", pageObject.get("statistics", {}).get("gear"))
    add_field("Senses", pageObject.get("senses"))
    add_field("Perception", pageObject.get("perception"))
    saves = []
    for save in ["fort", "ref", "will"]:
        if save in defense:
            saves.append({save.capitalize(): defense[save]})
    if saves:
        lines.append("saves:")
        for item in saves:
            for k, v in item.items():
                lines.append(f"  - {k}: {yaml_quote(v)}")
    for mod in defense.get("save_modifiers", []):
        lines.append(f"  - Other: {yaml_quote(mod)}")
    if pageObject.get("offense", {}).get("melee"):
        lines.append("Melee:")
        lines.append(f"  - name: Melee")
        lines.append(f"    desc: {yaml_quote(pageObject['offense']['melee'])}")
    if pageObject.get("offense", {}).get("ranged"):
        lines.append("Ranged:")
        lines.append(f"  - name: Ranged")
        lines.append(f"    desc: {yaml_quote(pageObject['offense']['ranged'])}")
    if pageObject.get("offense", {}).get("offensive_abilities"):
        lines.append("offabilities:")
        lines.append(f"  - name: Offensive Abilities")
        lines.append(f"    desc: {yaml_quote(pageObject['offense']['offensive_abilities'])}")
    spell_sections = pageObject.get("offense", {}).get("spells")
    if spell_sections:
        spell_lines = format_spell_sections(spell_sections)
        if spell_lines:
            lines.extend(yaml_list("Spells", spell_lines))
    special_abilities = parse_special_abilities(pageObject.get("special_abilities"))
    if special_abilities:
        lines.append("specialabil:")
        for item in special_abilities:
            lines.append(f"  - name: {item['name']}")
            lines.append(f"    desc: {yaml_quote(item['desc'])}")
    defabilities = parse_defensive_entries(defense)
    if defabilities:
        lines.append("defabilities:")
        for item in defabilities:
            lines.append(f"  - name: {item['name']}")
            lines.append(f"    desc: {yaml_quote(item['desc'])}")
    if pageObject.get("statistics", {}).get("other_abilities"):
        add_field("otherabil", pageObject['statistics']['other_abilities'])
    ecology = pageObject.get("ecology")
    if ecology and (ecology.get("environment") or ecology.get("organization")):
        lines.append("Ecology:")
        if ecology.get("environment"):
            lines.append(f"  - name: Environment")
            lines.append(f"    desc: {yaml_quote(ecology['environment'])}")
        if ecology.get("organization"):
            lines.append(f"  - name: Organization")
            lines.append(f"    desc: {yaml_quote(ecology['organization'])}")
        if ecology.get("environment"):
            add_field("Environment", ecology.get("environment"))
        if ecology.get("organization"):
            add_field("Organization", ecology.get("organization"))
    add_field("source", pageObject.get("source"))
    lines.append("statblock: true")
    lines.append("---")
    if pageObject.get("title1"):
        lines.append("```statblock")
        lines.append(f"creature: {yaml_quote(pageObject.get('title1'))}")
        lines.append("```")
    if pageObject.get("desc_long"):
        lines.append(pageObject["desc_long"])
    return "\n".join(lines).rstrip() + "\n"


def sanitize_filename(value):
    if not value:
        return "unnamed"
    value = re.sub('[\\/*?<>|:\\"]+', '', value)
    value = re.sub(r"\s+", "-", value.strip())
    value = re.sub(r"[^\w\-\.]+", "", value)
    return value or "unnamed"


def soft_assert(condition, message="Assertion failed"):
    """
    A replacement for assert that logs failures with the actual assertion code
    
    Args:
        condition: The condition to check
        message: Optional message to include in the log
    
    Returns:
        bool: True if the assertion passed, False if it failed
    """
    if not condition:
        # Get the caller's frame information
        caller_frame = inspect.currentframe().f_back
        filename = os.path.basename(caller_frame.f_code.co_filename)
        line_number = caller_frame.f_lineno
        
        # Get the source code of the line that called soft_assert
        line = linecache.getline(caller_frame.f_code.co_filename, line_number).strip()
        
        # Extract the condition from the source code
        # This pattern looks for soft_assert(...) and captures what's inside the parentheses
        import re
        match = re.search(r'soft_assert\s*\((.+?)(?:,)', line)
        condition_text = match.group(1).strip() if match else "unknown condition"
        
        # Log the failure with detailed information
        failure_msg = f"ASSERTION FAILED in {filename}:{line_number} - \"{condition_text}\" - {message}"
        logging.error(failure_msg)
        
        # You can optionally print to console as well
        print(f"WARNING: {failure_msg}")
        
        return False
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        datapath = sys.argv[1]
    else:
        datapath = "data/"

    logging.basicConfig(
        filename=os.path.join(datapath, 'assertion_failures.log'),
        level=logging.ERROR,
        format='%(asctime)s - %(message)s'
    )

    urls = []
    with open(os.path.join(datapath, "urls.txt")) as file:
        for line in file:
            urls.append(line.rstrip())

    broken_urls = []

    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "broken_urls.txt")
    with open(file_path) as file:
        for line in file:
            if not line.strip() == "" and not line.strip().startswith("#"):
                broken_urls.append(line.rstrip())

    pageObjects = {}
    base_datapath = datapath
    html_path = os.path.join(datapath, "html")
    if os.path.isdir(html_path):
        datapath = html_path
    for i, url in enumerate(tqdm(urls)):
        # Skip urls pre-marked as broken
        if url in broken_urls:
            continue

        with open(os.path.join(datapath, str(i) + ".html"), encoding='utf-8') as file:
            html = file.read()

        try:
            pageObjects[url] = parsePage(html, url)
        except Exception as e:
            print(url)
            # raise e
            _, _, tb = sys.exc_info()
            traceback.print_tb(tb)
            print(type(e).__name__ + ": " + str(e))

    markdown_dir = os.path.join(base_datapath, 'markdown')
    os.makedirs(markdown_dir, exist_ok=True)
    written_files = {}
    for url, pageObject in pageObjects.items():
        filename = sanitize_filename(pageObject.get('title1') or url)
        file_path = os.path.join(markdown_dir, f"{filename}.md")
        if filename in written_files:
            print(f"Overwriting file with matching name: {filename}.md (previously from {written_files[filename]})")
        written_files[filename] = url
        with open(file_path, 'w', encoding='utf-8') as md_file:
            md_file.write(render_markdown(pageObject))
