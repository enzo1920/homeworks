#!/usr/bin/python3.6


import re
import os
import sys
import urllib
import aiohttp
import asyncio
import logging
import hashlib
import argparse
import functools
import subprocess
import collections
from bs4 import BeautifulSoup
from urllib.parse import urlparse

YCOMB_URL = "https://news.ycombinator.com/"
YCOMB_TEMPLATE = "https://news.ycombinator.com/item?id={id}"
RETRY = 3
WAIT_AFTER_RETRY=2

FileExtentions = collections.namedtuple("FileExtentions", ["jpeg", "png", "pdf", "lon", "apps"])

class Storekeeper:

    def __init__(self, store_dir,loop):
        self.__posts_saved = 0
        self.__comments_links_saved = 0
        self.store_dir = store_dir
        self.loop =  loop

    def create_dirs(self, path):
        dirpath = os.path.dirname(path)
        os.makedirs(dirpath, exist_ok=True)

    def get_and_store(self, html):
        pass

    def get_path(self, link_id, post_id, url):
        file_ext = "html"
        if str(url).endswith("pdf"):
            file_ext="pdf"

        if link_id > 0:
            filename = "{}_{}.{}".format(post_id, link_id,file_ext)
        else:
            filename = "{}.{}".format(post_id,file_ext)
        filepath = os.path.join(self.store_dir, str(post_id), filename)
        return filepath


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


    def write_to_file(self, path, content):
        """
        Save binary content to file
        """
        try:
            self.create_dirs(path)
            with open(path, "wb") as f:
                f.write(content)
        except OSError as ex:
            logging.error("Can't save file {}. {}: {}".format(path, type(ex).__name__, ex.args))
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
            #filepath = os.path.join(self.store_dir, str(post_id))
            filepath = self.get_path(link_id, post_id, url)
            self.write_to_file(filepath, content)
            #logging.debug("Fetched and saved link {} for post {}: {}".format(link_id, post_id, url))
        except Exception as ex:
            logging.error("save err: {}".format(str(ex)))


    async def pdf_converter(self, url, post_id, link_id):
        """Run command in subprocess (shell)"""
        try:
            filepath = self.get_path(link_id, post_id, url)
            self.create_dirs(filepath)
            command = "xvfb-run wkhtmltopdf '{}', {}".format(url,filepath.replace('html','pdf'))
            # Create subprocess
            process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE)
            print('Started:', command, '(pid = ' + str(process.pid) + ')')

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                print('Done:', command, '(pid = ' + str(process.pid) + ')')
            else:
                print('Failed:', command, '(pid = ' + str(process.pid) + ')')
            result = stdout.decode().strip()
            print(result)
            return result
        except Exception as ex:
            logging.error("save err: {}".format(str(ex)))





async def get_links_from_comments(post_id, storekeeper):
    """
    Fetch comments page and parse links from comments
    """
    url = YCOMB_TEMPLATE.format(id=post_id)
    links = set()
    try:
        html = await storekeeper.get_body(url)
        soup = BeautifulSoup(html, "html5lib")
        for link in soup.select(".comment a[rel=nofollow]"):
            _url = link.attrs["href"]
            parsed_url = urlparse(_url)
            if parsed_url.scheme and parsed_url.netloc:
                print(_url)
                links.add(_url)

        return list(links)
    except aiohttp.ClientError:
        return list(links)



async def check_main_page(storekeeper, queue):
    html = await storekeeper.get_body(YCOMB_URL)
    #logging.info(html)
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


async def crawler(storekeeper, queue):

    while True:
        post_and_url = await queue.get()
        if post_and_url == None:
            logging.info("Worker got None exit")
            return
        else:
            post_id, url = post_and_url
        #print(post_and_url)
        ready_post_ids = storekeeper.get_created_dirs()
        if post_id in ready_post_ids:
            logging.debug("Post {} already saved".format(post_id))
            continue

        comments_links = await get_links_from_comments(post_id, storekeeper)
        links = [url] + comments_links
        print(links)
        #logging.debug("Worker {} - found {} links in post {}".format(w_id, len(links), post_id))

        converter_tasks = [
            storekeeper.pdf_converter(link, post_id, ind) for ind, link in enumerate(links)
        ]
        await asyncio.gather(*converter_tasks)
        '''tasks = [
            storekeeper.load_and_save(link, post_id, ind) for ind, link in enumerate(links)
        ]

        await asyncio.gather(*tasks)'''

async def monitor(storekeeper, queue):
    """
    Periodically check news.ycombinator.com for new articles.
    Parse articles and links from comments and save to local files
    """

    iteration = 1
    while True:
        logging.info("Start crawl: {} iteration".format(iteration))

        try:
            await check_main_page(storekeeper, queue)
        except Exception:
            logging.exception("Unrecognized error -> close all workers and exit")
            #for _ in range(num_workers):
            await queue.put(None)
            return
        iteration += 1
'''
        posts_saved = await fetcher.posts_saved
        comments_links_saved = await fetcher.comments_links_saved
        log.info("Saved {} posts, {} links from comments".format(
            posts_saved, comments_links_saved
        ))
        log.info("Waiting for {} sec...".format(to_sleep))
        await asyncio.sleep(to_sleep)'''






def main(args):
    loop = asyncio.get_event_loop()
    storekeeper = Storekeeper(args.storedir, loop)
    queue = asyncio.Queue(loop=loop)

    workers = [crawler(storekeeper, queue)]
    workers.append(monitor(storekeeper, queue))

    loop.run_until_complete(asyncio.gather(*workers))
    loop.close()

    #loop.run_until_complete(monitor_ycombinator(storekeeper, queue))
    '''workers = [
        worker_crawl_url(i, storekeeper, queue)
        for i in range(3)
    ]

    loop.run_until_complete(asyncio.gather(*workers))'''
    loop.close()
    #loop = asyncio.get_event_loop()
    #storekeeper =Storekeeper(args.storedir,loop)
    #loop.run_until_complete(get_body(client, YCOMB_URL))



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



