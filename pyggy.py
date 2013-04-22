# Pyggy
#
# Author: Anton Samson <anton@antonsamson.com>
# Available freely at: https://github.com/antsam/pyggy
#
# A web crawler that will save all the pages/files from a specific
# domain/subdomain onto disk.
#
# To start with default settings: python pyggy.py -v
# The -v flag will turn on verbose output so you can see what the
# crawler is currently doing.
#
# Currently does not deep crawl dynamic pages
# e.g. contains ?variable=something
#
# The crawler will save its visited and seed URLs every N page visits.
#
# TODO: Add multi-threading
# TODO: Add support for user authentication/login pages
# TODO: Ignore non HTTP links
#

import sys
import argparse
import hashlib
import os
from time import sleep
from random import randint
import lxml.html.clean
from urlparse import urlparse
import requests

args = []

# Constsants
CONST_HEADERS = {"User-Agent": "Pyggy 0.1 - https://github.com/antsam/pyggy"}
CONST_HTTP = "http://"
CONST_HTTPS = "https://"
CONST_RESUME_FILE_NAME = "resume.dat"
CONST_VISITED_FILE_NAME = "visited.dat"

CONST_DEFAULT_FRONTIER = "https://github.com/antsam/"
CONST_DEFAULT_BASE = "github.com/antsam/"
CONST_DEFAULT_SAVE_PATH = "./data/"
CONST_DEFAULT_SAVE_INTERVAL = int(5)
CONST_DEFAULT_FILE_NAME = "index.html"
CONST_DEFAULT_MIN_WAIT = int(10)
CONST_DEFAULT_MAX_WAIT = int(15)
CONST_DEFAULT_TIMEOUT = int(10)

# Shared variables
_visited = set()
_seeds = set()

# Make a thread sleep
def throttle(lower, upper):
    wait = randint(lower, upper)
    if(args.verbose):
        print "Sleeping for " + str(wait) + " seconds"
    sleep(wait)

# Is this document parsable?
def is_text(header):
    return header.startswith("text/")

# Get the SHA1 checksum of a file
def file_checksum(fp, block_size = 2**20):
    sha1 = hashlib.sha1()
    while True:
        data = fp.read(block_size)
        if not data:
            break
        sha1.update(data)
    return sha1.hexdigest()

# Get the SHA1 hash of a String
def checksum(text):
    return hashlib.sha1(text).hexdigest()

# Calculate sha1 of URL
def get_url_hash(url):
    return hashlib.sha1(url.lower()).hexdigest()

# Determines a suitable save directory for a given URL
def get_save_dir(url, skip = 1):
    parsed = urlparse(url)
    dir_path = parsed.path.split("/")
    if len(dir_path) >= 2:
        dir_path = args.dir + parsed.netloc + "/".join(dir_path[:(-1 * skip)]) + "/"
    else:
        dir_path = args.dir + parsed.netloc + "/"
    return dir_path.replace("//", "/")

# Choose an appropriate filename
# May not always have a file extension
def get_file_name(url, skip = 1):
    parsed = urlparse(url)
    file_name = parsed.path.split("/")
    if (len(file_name) >= 2) and file_name[-1 * skip]:
        return file_name[-1 * skip]
    return None

# Has the URL been _visited before?
def been_visited(url):
    hashed = get_url_hash(url)
    if hashed in _visited:
        if args.verbose:
            print "This URL has already been _visited: " + url
        return True
    _visited.add(hashed)
    return False

# Visit a URL and save it to disk
# Print URL before showing error
def visit(url, base):
    if been_visited(url):
        return
    try:
        req = requests.get(url, stream=True, headers=CONST_HEADERS, timeout=args.timeout)
    except:
        print "Error: Could not retrieve URL: " + url
        return
    final_url = url
    if len(req.history) > 0:
        final_url = normalize_url(req.url)
        if been_visited(final_url):
            return
    save_dir = get_save_dir(final_url)
    if req.status_code == 200:
        raw_data = req.content
        can_parse = is_text(req.headers["content-type"])
        if can_parse:
            if args.verbose:
                print "URL appears to contain text content."
            if args.clean:
                cleaned = lxml.html.clean.clean_html(raw_data)
        elif args.verbose:
            print "URL data does not appear to contain text content."
        file_name = get_file_name(final_url)
        if (not file_name) and can_parse:
            file_name = CONST_DEFAULT_FILE_NAME
        elif not file_name:
            save_dir = get_save_dir(final_url, 2)
            file_name = get_file_name(final_url, 2)
        file_path = save_dir + file_name
        if args.verbose:
            print "Starting URL: " + url
            print "Final URL: " + final_url
            print "Save directory: " + save_dir
            print "File name: " + file_name
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir)
            except:
                print "Error: Received malformed URL."
                return
        if os.path.isfile(file_path):
            # do checksums
            fh = open(file_path, "r+")
            local_checksum = file_checksum(fh)
            # TODO: Simplify first two conditions
            if args.clean and (checksum(cleaned) == local_checksum) and args.verbose:
                print "Page content has not changed."
                cleaned = None
            elif (checksum(raw_data) == local_checksum) and args.verbose:
                print "Page content has not changed."
            else:
                # Overwrite old data
                if args.verbose:
                    print "Page content has changed since last visit."
                fh.seek(0)
                if args.clean and can_parse:
                    fh.write(cleaned)
                    cleaned = None
                else:
                    fh.write(raw_data)
                fh.truncate()
            fh.close()
        else:
            fh = open(file_path, "w")
            if can_parse and args.clean:
                fh.write(cleaned)
                cleaned = None
            else:
                fh.write(raw_data)
            fh.close()
        if can_parse:
            get_links(url, base, raw_data)
        raw_data = None
    else:
        print "Warning: Received HTTP status code: " + str(req.status_code)
        return

# Normalizes URLs
def normalize_url(url):
    parsed = urlparse(url)
    url_base = parsed.netloc
    url_path = parsed.path
    if ("." not in url_path) and ((not url_path) or parsed.fragment):
        url_path += "/"
    url_path = url_path.replace("//", "/")
    return parsed.scheme + "://" + url_base + url_path

def in_domain(url, domain):
    parsed = urlparse(url)
    return ((parsed.scheme in CONST_HTTPS) and (domain.netloc in parsed.netloc) and (domain.path in parsed.path))

# Query for links
def query_links(query, domain):
    links = [normalize_url(link) for link in query if in_domain(link, domain)]
    return links

# Parse HTML for links
def get_links(url, base, html):
    try:
        dom = lxml.html.fromstring(html, base_url=CONST_HTTP+base)
    except:
        print "Error: Could not parse file!"
        return
    dom.make_links_absolute(url)
    domain = urlparse(CONST_HTTP + base)
    # TODO: Make this shorter
    links = query_links(dom.xpath("//a/@href"), domain) + query_links(dom.xpath("//frame/@src"), domain) + query_links(dom.xpath("//iframe/@src"), domain)
    if args.verbose:
        print "Newly found links: " + str(len(links))
    dom = None
    for link in links:
        if(get_url_hash(link) not in _visited):
            _seeds.add(str(link))

# Load a set from disk
def load_set(name):
    if os.path.isfile(args.dir + name):
        fh = open(args.dir + name, "r")
        resume_data = {normalize_url(line.rstrip()) for line in fh.readlines()}
        fh.close()
        return resume_data
    resume_data = set()
    return resume_data

# Save a set to disk
def save_set(name, data):
    if not os.path.isfile(args.dir + name):
        if not os.path.exists(args.dir):
            os.makedirs(args.dir)
        fh = open(args.dir + name, "w")
    else:
        fh = open(args.dir + name, "r+")
        fh.seek(0)
    for line in data:
        fh.write("%s\n" % line)
    fh.truncate()
    fh.close()

def verify_args():
    args.frontier = normalize_url(args.frontier)
    if args.dir[-1] != "/":
        args.dir += "/"
    if not isinstance(args.max, (int, long)) or (args.max <= 0):
        args.max = CONST_DEFAULT_MAX_WAIT
    if not isinstance(args.min, (int, long)) or (args.min <= 0):
        args.min = CONST_DEFAULT_MIN_WAIT
    if args.min >= args.max:
        args.min = CONST_DEFAULT_MIN_WAIT
        args.max = CONST_DEFAULT_MAX_WAIT
    if not isinstance(args.interval, (int, long)) or (args.interval <= 0):
        args.interval = CONST_DEFAULT_SAVE_INTERVAL
    if not isinstance(args.timeout, (int, long)) or (args.timeout <= 0):
        args.timeout = CONST_DEFAULT_TIMEOUT

def test():
    return

# Main
if __name__ == "__main__":
    # Parse any command line args
    parser = argparse.ArgumentParser(description="Crawls a domain and downloads copies of each URL _visited.")
    parser.add_argument("-b", "--base", help="sets the absolute base for a URL, e.g. www.github.com/", default=CONST_DEFAULT_BASE)
    parser.add_argument("-d", "--dir", help="sets the location of where to save crawl data", default=CONST_DEFAULT_SAVE_PATH)
    parser.add_argument("-f", "--frontier", help="sets the crawl frontier, e.g. https://www.github.com/antsam", default=CONST_DEFAULT_FRONTIER)
    parser.add_argument("-i", "--interval", help="sets the save interval for the URL seed and _visited list", type=int, default=CONST_DEFAULT_SAVE_INTERVAL)
    parser.add_argument("-m", "--min", help="sets the minimum wait time in seconds before each crawl", type=int, default=CONST_DEFAULT_MIN_WAIT)
    parser.add_argument("-x", "--max", help="sets the maximum wait time in seconds before each crawl", type=int, default=CONST_DEFAULT_MAX_WAIT)
    parser.add_argument("-w", "--timeout", help="sets the maximum time to wait in seconds for a URL to load", type=int, default=CONST_DEFAULT_TIMEOUT)
    parser.add_argument("-r", "--resume", help="resumes crawling from where we last left off", action="store_true")
    parser.add_argument("-v", "--verbose", help="enables verbose output", action="store_true")
    parser.add_argument("-c", "--clean", help="HTML data will be cleaned before saving", action="store_true")
    args, unknown = parser.parse_known_args()
    # Normalize user input
    # check that none of the args are invalid, e.g. timeouts and data dirs
    verify_args()
    if args.verbose:
        print args
        print unknown
    print "Crawler has started!"
    print "Frontier: " + args.frontier
    print "Base URL: " + args.base
    # Populate _seeds
    if args.resume:
        # Load _seeds and _visited from disk
        if(args.verbose):
            print "Loading seed URLs from disk."
        _seeds.update(load_set(CONST_RESUME_FILE_NAME))
        _visited.update(load_set(CONST_VISITED_FILE_NAME))
        if len(_seeds) > 0:
            domain = urlparse(CONST_HTTP + args.base)
            seed = _seeds.pop()
            if not in_domain(seed, domain):
                print seed
                sys.exit("Fatal Error: URL does not belong to the current site! Resumed from wrong site data?")
            visit(seed, args.base)
        else:
            print "Error: Could not load seed URLs from disk. Defaulting to frontier."
            visit(args.frontier, args.base)
    else:
        if args.verbose:
            print "Collecting seed URLs from the frontier!"
        visit(args.frontier, args.base)
    throttle(args.min, args.max)
    crawled = 0
    while len(_seeds) > 0:
        print "Current number of seeds: " + str(len(_seeds))
        visit(_seeds.pop(), args.base)
        crawled += 1
        throttle(args.min, args.max)
        if crawled % args.interval == 0:
            if args.verbose:
                print "Saving seed URLs to disk."
            save_set(CONST_RESUME_FILE_NAME, _seeds)
            if args.verbose:
                print "Saving visited URLs to disk."
            save_set(CONST_VISITED_FILE_NAME, _visited)
    print "Crawler has finished!"
