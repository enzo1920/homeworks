#!/usr/bin/python3.5


import re
import os
import sys
import urllib
import aiohttp
import asyncio
import logging
import hashlib
import argparse
import subprocess
from bs4 import BeautifulSoup
#from urllib.parse import urljoin, urldefrag

YCOMB_URL = "https://news.ycombinator.com/"
YCOMB_TEMPLATE = "https://news.ycombinator.com/item?id={id}"
RETRY = 3
WAIT_AFTER_RETRY=2

class Storekeeper:

    def __init__(self, store_dir):
        self.__posts_saved = 0
        self.__comments_links_saved = 0
        self.store_dir = store_dir

    def create_dirs(self, path):
        dirpath = os.path.dirname(path)
        os.makedirs(dirpath, exist_ok=True)

    def get_and_store(self, html):
        pass

    def get_path(self, link_id, post_id):
        pass

    def get_created_dirs(self):
        self.create_dirs(self.store_dir)
        post_ids = set()
        for subdir_name in os.listdir(self.store_dir):
            if os.path.isdir(os.path.join(self.store_dir, subdir_name)):
                try:
                    post_id = int(subdir_name)
                    post_ids.add(post_id)
                except ValueError:
                    logging.error("Subdir name not contain id {}".format(subdir_name))

        return post_ids


    def filename_from_url_gen(self, url):
        hash_url = hashlib.md5(url.encode())
        return hash_url.hexdigest().join('.pdf')


    async def write_to_pdf(self, path, url):
         '''save url to pdf using wkhtmltopdf'''
        try:
            '''shoot into my leg )))'''
            '''if pdf ?)))) add check to pdf'''
            self.create_dirs(path)
            fname = filename_from_url_gen(url)
            writepdf_command = "wkhtmltopdf {} {}".format(url, fname)
            proc_write_pdf = subprocess.Popen(some_command, stdout=subprocess.PIPE, shell=True)
            output, err = proc_write_pdf.communicate()
            p_status = proc_write_pdf.wait()

        except OSError as ex:
            log.error("Can't save file {}. {}: {}".format(path, type(ex).__name__, ex.args
            ))
            return


    async def get_body(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                        return await response.read()
        except aiohttp.ClientError as ex:
            logging.error("aiohttp can't read response: %s" % ex)


    async def load_and_save(self, url, post_id, link_id):
        """
        Fetch url and save content to file
        """
        try:
            content = await self.get_body(url)
            filepath = self.get_path(link_id, post_id)
            self.write_to_file(filepath, content)
            log.debug("Fetched and saved link {} for post {}: {}".format(link_id, post_id, url))
        except aiohttp.ClientError:
            pass



def get_links_from_comments(post_id):
    #comments  and parse links from comments
    url = YCOMB_POST_URL_TEMPLATE.format(id=post_id)
    print(url)



async def check_main_page(storekeeper, queue):
    html = await storekeeper.get_body(YCOMB_URL)

    posts = parse_main_page(html)
    ready_post_ids = storekeeper.get_created_dirs()

    not_ready_posts = {}
    for p_id, p_url in posts.items():
        if p_id not in ready_post_ids:
            not_ready_posts[p_id] = p_url
        else:
            logging.debug("Post {} already parsed".format(p_id))

    for p_id, p_url in not_ready_posts.items():
        await queue.put((p_id, p_url))


def parse_main_page(html):
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
            logging.error("Error on {} post (id: {}, url: {})".format(ind, id, url))
            continue
    return posts


async def crawl_urls_worker(w_id, storekeeper, queue):

    while True:
        post_and_url = await queue.get()
        if post_and_url == None:
            logging.info("Worker {} got None exit".format(w_id))
            return
        else:
            post_id, url = post_and_url

        ready_post_ids = storekeeper.get_dir_names()
        if post_id in ready_post_ids:
            log.debug("Post {} already saved".format(post_id))
            continue

        comments_links = await get_links_from_comments(post_id, fetcher)
        links = [url] + comments_links
        logging.debug("Worker {} - found {} links in post {}".format(w_id, len(links), post_id))

        tasks = [
            storekeeper.load_and_save(link, post_id, ind) for ind, link in enumerate(links)
        ]

        await asyncio.gather(*tasks)






def main(args):

    loop = asyncio.get_event_loop()
    #client = aiohttp.ClientSession(loop=loop)
    #raw_html = loop.run_until_complete(get_body(client,YCOMB_URL))
    storekeeper =Storekeeper(args.storedir)
    loop.run_until_complete(get_body(client, YCOMB_URL))
    #parse_main_page(raw_html)
    #client.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log", action="store", default="crawler.log")
    parser.add_argument("-s", "--storedir", action="store", default="./storedir/")
    parser.add_argument("--dry", action="store_true", default=False)
    args = parser.parse_args()
    logging.basicConfig(filename=args.log, level=logging.INFO if not args.dry else logging.DEBUG,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')

    logging.info("Hackernews srarted with options: %s" % args)
    try:
        main(args)
    except Exception as e:
        logging.exception("Unexpected error: %s" % e)
        sys.exit(1)



