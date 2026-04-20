from bs4 import BeautifulSoup
import requests
import re
from urllib.parse import urljoin
import os
from tqdm.auto import tqdm
from pathlib import Path
import json


def extract_hit_points(soup, html, url):
    elem = soup.find('b', string=re.compile(r'Hit Points', re.I))
    if elem is not None:
        sibling = elem.next_sibling
        while sibling is not None and (not isinstance(sibling, str) or not sibling.strip()):
            sibling = sibling.next_sibling
        if sibling is not None:
            result = re.search(r":\s*(\d+)", str(sibling))
            if result:
                return int(result.group(1))

    result = re.search(r"<b>\s*Hit Points\s*</b>\s*:\s*(\d+)", html, re.I)
    if result:
        return int(result.group(1))

    for table in soup.select('table.inner'):
        headers = [th.get_text(strip=True) for th in table.select('tr:first-child b')]
        if 'Hit Points' in headers:
            hp_index = headers.index('Hit Points')
            first_row = table.select_one('tr:nth-of-type(2)')
            if first_row is not None:
                cells = [td.get_text(strip=True) for td in first_row.select('td')]
                if hp_index < len(cells):
                    cell = cells[hp_index]
                    result = re.search(r"(\d+)", cell)
                    if result:
                        return int(result.group(1))

    raise AssertionError(url)


if __name__ == "__main__":
    url_classes = "https://aonsrd.com/Classes.aspx"
    outfile = "data/class_hds.json"

    classes = {}

    # Create output directory if it doesn't exist
    Path(os.path.dirname(outfile)).mkdir(parents=True, exist_ok=True)

    # Classes
    # =======

    # Class list page
    html = requests.get(url_classes).text
    soup = BeautifulSoup(html, "html.parser")
    elems = soup.select("#ctl00_MainContent_FullClassList a")
    if not elems:
        elems = soup.select("a[href^='Classes.aspx?ItemName=']")

    entries = []
    for e in elems:
        href = e['href']
        entries.append((e.get_text().strip(), urljoin(url_classes, href)))

    # Get hit points from individual pages
    for name, url in tqdm(entries):
        name = name.strip()
        html = requests.get(url).text
        soup = BeautifulSoup(html, "html.parser")
        classes[name] = extract_hit_points(soup, html, url)

    # Write the results to disk
    with open(outfile, 'w') as fp:
        json.dump(classes, fp, indent=2)
