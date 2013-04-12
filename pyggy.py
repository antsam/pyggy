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
# TODO: Switch to urlparse and possibly Requests
# TODO: Add support for user authentication/login pages
#

import sys
import argparse
import urllib2
import hashlib
import os
from time import sleep
from random import randint
import lxml.html.clean

# Constsants
CONST_HEADERS = {"User-Agent": "Pyggy 0.1 - https://github.com/antsam/pyggy"}
CONST_HTTP = "http://"
CONST_HTTPS = "https://"
CONST_RESUME_FILE_NAME = "resume.dat"
CONST_VISITED_FILE_NAME = "visited.dat"

CONST_DEFAULT_FRONTIER = "https://github.com/antsam/pyggy"
CONST_DEFAULT_BASE = "github.com/antsam/"
CONST_DEFAULT_SAVE_PATH = "./data/"
CONST_DEFAULT_SAVE_INTERVAL = int(5)
CONST_DEFAULT_MIN_WAIT = int(10)
CONST_DEFAULT_MAX_WAIT = int(15)
CONST_DEFAULT_MAX_SIZE = int(1048576)

# Shared variables
visited = set()
seeds = set()
args = []

# Make a thread sleep
def throttle(lower, upper):
	wait = randint(lower, upper)
	if(args.verbose):
		print "Sleeping for " + str(wait) + " seconds"
	sleep(wait)

# Is this document parsable?
def is_text(header):
	if "content-length" in header:
		file_size = int(header["content-length"])
	else:
		file_size = 0
	return header["content-type"].startswith("text/") and (file_size >= 0) and (file_size <= CONST_DEFAULT_MAX_SIZE)

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
def get_save_path(url):
	save_path = url.replace(CONST_HTTP, "")
	save_path = save_path.replace(CONST_HTTPS, "")
	save_path = save_path.lower().split("/")[:-1]
	if len(save_path) == 0:
		save_path = args.dir
	elif len(save_path) == 1:
		save_path = args.dir + save_path[0] + "/"
	else:
		save_path = args.dir + "/".join(save_path) + "/"
	save_path = save_path.replace("//", "/")
	return save_path

# Visit a URL and save it to disk
def visit(url, base):
	url_hash = get_url_hash(url)
	if url_hash in visited:
		if args.verbose:
			print "This URL has already been visited: " + url
		return
	else:
		visited.add(url_hash)
	# Download the current URL
	req = urllib2.Request(url, None, CONST_HEADERS)
	try:
		raw = urllib2.urlopen(req)
	except urllib2.URLError, e:
		print "Received HTTP error from: " + url
		if hasattr(e, "code") and e.code:
			print "Status code was: " + str(e.code)
		return
	else:
		can_parse = is_text(raw.info().dict)
		# Determine where to save the data
		save_path = get_save_path(url)
		file_name = url.lower().split("/")[-1]
		if can_parse:
			if (not file_name) or ("." not in file_name):
				save_path = save_path + file_name
				file_name = "/index.html"
		file_path = save_path + file_name
		file_path = file_path.replace("//", "/")
		if args.verbose:
			print "URL: " + url
			print "Save path: " + save_path
			print "File path: " + file_path
		# TODO: check that we have enough RAM to store the raw file in memory.
		# TODO: move the file writes to their own function
		raw_data = raw.read()
		if can_parse and args.clean:
			cleaned = lxml.html.clean.clean_html(raw_data)
		if not os.path.isfile(file_path):
			if not os.path.exists(save_path):
				os.makedirs(save_path)
			fh = open(file_path, "w")
			if can_parse:
				if(args.verbose):
					print "URL has text content."
				if(args.clean):
					fh.write(cleaned)
					cleaned = None
				else:
					fh.write(raw_data)
				fh.close()
				get_links(url, base, raw_data)
			else:
				if(args.verbose):
					print "URL is binary or non-text."
				fh.write(raw_data)
				fh.close()
			raw_data = None
		else:
			# Do a checksum to see if the URL's content has changed
			# Load data from file cache
			# TODO: check mime-type of file before opening
			fh = open(file_path, "r+")
			local_checksum = file_checksum(fh)
			if args.clean and (checksum(cleaned) == local_checksum) and args.verbose:
				print "Page content has not changed."
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
			if can_parse:
				get_links(url, base, raw_data)
			raw_data = None

# Strip anchors and dynamic content from URLs
def strip_url(url):
	new_url = url
	if "?" in url:
		new_url = new_url[0:new_url.find("?")]
	if "#" in url:
		new_url = new_url[0:new_url.find("#")]
	return new_url

# Query for links
def query_links(query, base):
	links = [strip_url(link) for link in query if(link.startswith(CONST_HTTP+base)) or (link.startswith(CONST_HTTPS+base))]
	return links

# Parse HTML for links
def get_links(url, base, html):
	try:
		dom = lxml.html.fromstring(html, base_url=CONST_HTTP+base)
	except:
		print "Error: Could not parse file!"
		return
	dom.make_links_absolute(url)
	links = query_links(dom.xpath("//a/@href"), base) + query_links(dom.xpath("//frame/@src"), base) + query_links(dom.xpath("//iframe/@src"), base)
	dom = None
	for link in links:
		hashed = get_url_hash(link)
		if(hashed not in visited):
			seeds.add(str(link))

# Load a set from disk
def load_set(name):
	if os.path.isfile(args.dir + name):
		fh = open(args.dir + name, "r")
		resume_data = {line.rstrip() for line in fh.readlines()}
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


# Main
if __name__ == "__main__":
	# Parse any command line args
	parser = argparse.ArgumentParser(description="Crawls a domain and downloads copies of each URL visited.")
	parser.add_argument("-b", "--base", help="sets the absolute base for a URL, e.g. www.github.com/", default=CONST_DEFAULT_BASE)
	parser.add_argument("-d", "--dir", help="sets the location of where to save crawl data", default=CONST_DEFAULT_SAVE_PATH)
	parser.add_argument("-f", "--frontier", help="sets the crawl frontier, e.g. https://www.github.com/antsam", default=CONST_DEFAULT_FRONTIER)
	parser.add_argument("-i", "--interval", help="sets the save interval for the URL seed and visited list", type=int, default=CONST_DEFAULT_SAVE_INTERVAL)
	parser.add_argument("-m", "--min", help="sets the minimum wait time in seconds before each crawl", type=int, default=CONST_DEFAULT_MIN_WAIT)
	parser.add_argument("-x", "--max", help="sets the maximum wait time in seconds before each crawl", type=int, default=CONST_DEFAULT_MAX_WAIT)
	parser.add_argument("-r", "--resume", help="resumes crawling from where we last left off", action="store_true")
	parser.add_argument("-v", "--verbose", help="enables verbose output", action="store_true")
	parser.add_argument("-c", "--clean", help="HTML data will be cleaned before saving", action="store_true")
	args, unknown = parser.parse_known_args()
	if args.verbose:
		print args
		print unknown
	print "Crawler has started!"
	print "Frontier: " + args.frontier
	print "Base URL: " + args.base
	# Populate seeds
	if args.resume:
		# Load seeds and visited from disk
		if(args.verbose):
			print "Loading seed URLs from disk."
		seeds.update(load_set(CONST_RESUME_FILE_NAME))
		visited.update(load_set(CONST_VISITED_FILE_NAME))
		if len(seeds) > 0:
			seed = seeds.pop()
			if (args.base not in seed) and (args.base[:-1] not in seed):
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
	while len(seeds) > 0:
		print "Current number of seeds: " + str(len(seeds))
		visit(seeds.pop(), args.base)
		crawled += 1
		throttle(args.min, args.max)
		if crawled % CONST_DEFAULT_SAVE_INTERVAL == 0:
			if args.verbose:
				print "Saving seed URLs to disk."
			save_set(CONST_RESUME_FILE_NAME, seeds)
			if args.verbose:
				print "Saving visited URLs to disk."
			save_set(CONST_VISITED_FILE_NAME, visited)
	print "Crawler has finished!"
