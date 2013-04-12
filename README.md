Pyggy
=====

A Python web crawler designed to save a copy of an entire website to disk.

## Features
### Resumable Crawls
After a user defined number of page visits, the crawler will save its current crawl state to disk. If for some reason
you wish to stop the crawler, you may restart it from its last saved state by starting the crwaler the `-r` flag.

    python pyggy.py -v -bgithub.com/antsam -fhttps://github.com/antsam -r

To set the number of page visits before the crawler should save its state, start the crawler with the `-i` flag 
followed by an integer.

### Works with multiple website
Pyggy will generate an HTML snapshot of the website you wish to crawl. Any files or pages that are linked to and are 
local to the domain being crawled will be saved in the data directory. Currently, images that are not specifically 
linked to by a URL will not be saved to disk.

### Sanitized HTML
HTML downloaded from a website can be sanitized before being saved to disk by starting the crawler with the `-c` flag.

Please note that **libxml** should be installed for this feature to work.

### Page/File Freshness
Pyggy will only download a previously visited URL to disk if said URL has been recently changed. A future release will
incorporate the data file's timestamp into account.

## Command line arguments
<pre>usage: pyggy.py [-h] [-b BASE] [-d DIR] [-f FRONTIER] [-i INTERVAL] [-m MIN]
                [-x MAX] [-r] [-v] [-c]

Crawls a domain and downloads copies of each URL visited.

optional arguments:
  -h, --help            show this help message and exit
  -b BASE, --base BASE  sets the absolute base for a URL, e.g. www.github.com/
  -d DIR, --dir DIR     sets the location of where to save crawl data
  -f FRONTIER, --frontier FRONTIER
                        sets the crawl frontier, e.g.
                        https://www.github.com/antsam
  -i INTERVAL, --interval INTERVAL
                        sets the save interval for the URL seed and visited
                        list
  -m MIN, --min MIN     sets the minimum wait time in seconds before each
                        crawl
  -x MAX, --max MAX     sets the maximum wait time in seconds before each
                        crawl
  -r, --resume          resumes crawling from where we last left off
  -v, --verbose         enables verbose output
  -c, --clean           HTML data will be cleaned before saving</pre>

## Example Usage
Starting Pyggy with the following command line arguments will set the crawler to download all pages and files
hosted on `https://github.com/antsam` and sets a minimum wait time of `5` seconds and a maximum wait of `10` seconds
in between each page visit:

    python pyggy.py -v -bgithub.com/antsam -fhttps://github.com/antsam -m5 -x10

If you wish to download all the pages on `github.com` but start from `https://github.com/antsam`:

    python pyggy.py -v -bgithub.com/ -fhttps://github.com/antsam

To disable verbose output, simply start Pyggy without the `-v` flag.

    python pyggy.py -bgithub.com/ -fhttps://github.com/antsam

If you wish to change the path of where the crawler saves its data, add a `-d` flag 
and make sure that it includes a trailing slash:

    python pyggy.py -v -bgithub.com/ -fhttps://github.com/antsam -d/path/to/your/data/

## Upcoming Features
* Multithreading
* Crawling based on stored data's age.
* Better handle dynamic webpages like calendars or forums.
* Adoption of urlparse and the Request library.

## Changelog
* April 11, 2013 - User friendly filenames are now used for stored data.
