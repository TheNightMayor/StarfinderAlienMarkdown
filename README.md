# PathfinderMonsterDatabase
A database of all monsters in Pathfinder 1e, created by parsing aonprd.com

## Setup

Run the following line to install all required libraries:
```
pip install -r requirements.txt
```

## Downloading and parsing the data
1. Run `download_page_list.py` in order to download the list of monster entry URLs:

```
python download_page_list.py
```

By default, this will get all monsters, NPCs, and mythic monsters.
You can also specify a URL as a parameter to the script to get just the monster entries from there (e.g. https://aonprd.com/Monsters.aspx?Letter=All).
Alternatively, you can just create the `data/urls.txt` file yourself.

2. Run `download_pages.py` to download each individual monster entry page:

```
python download_pages.py
```

This will take a bit. The script limits itself to a maximum of 5 requests a second to not overload aonprd.com, but you can adjust this number if you are still having trouble.
You can also give additional parameters to the script if you want to pull from a different file other than `data/urls.txt`, or if you want to write the results to a folder other than `data`.

3. Run `get_classes.py` to download a list of all classes, which will be used for parsing the data.

4. Run `main.py` to parse the raw HTML into .md files:

```
python main.py
```

This script is where the magic happens. If you want to adjust anything from adding special cases, changing how parsing is done, or changing the output format of the database, you'll need to change it here.
The script will pull from the `data/html` folder by default, but you can give it a different folder as an argument (where it will look for a `urls.txt` and appropriately named html files).
This script will also look for the `broken_urls.txt` file, which contains all URLs to ignore, usually because their HTML is broken or their monster statblocks are malformed in some way.
It will then create .md files with yaml properties for obsidian.md, specifically used with the fantasy statblocks plugin in a `data/markdown` folder.

