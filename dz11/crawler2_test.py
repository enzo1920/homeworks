#!/usr/bin/python3.5

# python 3.5 async web crawler.
# https://github.com/mehmetkose/python3.5-async-crawler

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2016 Mehmet Kose mehmet@linux.com

import re
import aiohttp
import asyncio
import urllib
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urldefrag

root_url = "http://news.ycombinator.com"
crawled_urls = []
#url_hub = [root_url, "%s/robots.txt" % (root_url), "%s/sitemap.xml" % (root_url)]

async def get_body(client, url):
    async with client.get(url) as response:
        return await response.read()

def remove_fragment(url):
    pure_url, frag = urldefrag(url)
    #print(pure_url)
    return pure_url

def html_parser():
    html_page = urllib.request.urlopen("http://news.ycombinator.com")
    soup = BeautifulSoup(html_page)
    for link in soup.findAll('a'):
        print(link.get('href'))


def get_links(html):
    new_urls = [link.split('"')[0] for link in str(html).replace("'",'"').split('href="')[1:]]
    print(new_urls)
    return [urljoin(root_url, remove_fragment(new_url)) for new_url in new_urls]

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    client = aiohttp.ClientSession(loop=loop)
    raw_html = loop.run_until_complete(get_body(client, root_url))
    for link in get_links(raw_html):
        if root_url in link and not link in crawled_urls:
            #url_hub.append(link)
    #url_hub.remove(to_crawl)
            crawled_urls.append(link)
            print("url  crawled: %s  " %  link)
    client.close()
    #html_parser()