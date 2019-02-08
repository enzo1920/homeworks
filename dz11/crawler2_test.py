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

def html_parser(html_page):
    soup = BeautifulSoup(html_page)
    for a in soup.find_all('a', href=True):
        print("Found the URL:", a['href'])

def parse_main_page(html):
    """
    Parse articles urls and their ids
    """
    posts = {}

    soup = BeautifulSoup(html, "html5lib")
    trs = soup.select("table.itemlist tr.athing")
    for ind, tr in enumerate(trs):
        id, url = "", ""
        try:
            id = int(tr.attrs["id"])
            url = tr.select_one("td.title a.storylink").attrs["href"]
            posts[id] = url
        except KeyError:
            log.error("Error on {} post (id: {}, url: {})".format(
                ind, id, url
            ))
            continue

    print(posts)



def get_links(html):
    new_urls = [link.split('"')[0] for link in str(html).replace("'",'"').split('href="')[1:]]
    return [urljoin(root_url, remove_fragment(new_url)) for new_url in new_urls]

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    client = aiohttp.ClientSession(loop=loop)
    raw_html = loop.run_until_complete(get_body(client, root_url))
    #html_parser(raw_html)
    parse_main_page(raw_html)
    '''for link in get_links(raw_html):
        if root_url in link and not link in crawled_urls:
            #url_hub.append(link)
            #crawled_urls.append(link)
            print("url  crawled: %s  " %  link)'''
    client.close()
    #html_parser()