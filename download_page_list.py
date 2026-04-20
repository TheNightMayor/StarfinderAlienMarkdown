from bs4 import BeautifulSoup
import requests
import sys
import traceback
from urllib.parse import quote, urljoin, urlparse, parse_qsl
import os
from pathlib import Path


if __name__ == "__main__":
	if len(sys.argv) > 1:
		pagelisturls = sys.argv[1:]
	else:
		pagelisturls = ["https://aonsrd.com/Aliens.aspx?Letter=All"]
	
	outfile = "data/urls.txt"

	# Create output directory if it doesn't exist
	Path(os.path.dirname(outfile)).mkdir(parents=True, exist_ok=True)

	allurls = []

	for url in pagelisturls:
		# Download page
		try:
			html = requests.get(url).text
		except requests.exceptions.RequestException as e:
			print(url)
			_, _, tb = sys.exc_info()
			traceback.print_tb(tb)
			print(type(e).__name__ + ": " + str(e))

		# Parse page
		soup = BeautifulSoup(html, "html.parser")
		elems = soup.select("#main table tr td:first-child a")
		urls = []
		for e in elems:
			href = e['href']
			full_url = urljoin(url, href)
			parsed = urlparse(full_url)
			encoded_query = "&".join(
				f"{quote(name, safe='')}={quote(value, safe='/()')}"
				for name, value in parse_qsl(parsed.query, keep_blank_values=True)
			)
			urls.append(parsed._replace(query=encoded_query).geturl())
		allurls += urls
		
	# Remove duplicates and sort
	allurls = sorted(list(set(allurls)))

	# Write the URL list to disk
	with open(outfile, 'w') as fp:
		fp.write("\n".join(allurls))