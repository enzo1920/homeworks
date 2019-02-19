#!/usr/bin/python3.6
#coding: utf-8

import os
import sys
import aiohttp
import asyncio
import logging
import argparse
import mimetypes
from email import encoders
from smtplib import SMTP_SSL as SMTP
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from email.mime.multipart import MIMEMultipart
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.header import Header

YCOMB_URL = "https://news.ycombinator.com/"
YCOMB_TEMPLATE = "https://news.ycombinator.com/item?id={id}"
RETRY = 3
WAIT_AFTER_RETRY=20

FILTERS=['arduino','raspberrypi','camera','streaming','diy','girls','farm','robots','sql','huawei','server']
SMTP_DICT = {"server":"smtp.yandex.ru:465","mail_from":"carlcrawl@yandex.ru","mail_pass":"wrxsti14", "mail_destination":"enzo1920@ya.ru", "timeout_smtp":"20"}


class MailWorker(object):
    def __init__(self, smtp_cfg_dict):
        self.smtp_server = smtp_cfg_dict['server']
        self.mail_from = smtp_cfg_dict['mail_from']
        self.mail_pass = smtp_cfg_dict['mail_pass']
        self.mail_destination = smtp_cfg_dict['mail_destination']
        self.timeout = smtp_cfg_dict['timeout_smtp']


    def attach_send(self, subject,file_to_send):
        server =self.smtp_server
        msg = MIMEMultipart()
        msg['From'] = self.mail_from
        msg['To'] = self.mail_destination
        msg['Subject'] = subject

        ctype, encoding = mimetypes.guess_type(file_to_send)
        if ctype is None or encoding is not None:
           ctype = 'application/octet-stream'
        maintype, subtype = ctype.split("/", 1)
        if maintype == "text":
           with open(file_to_send) as fsend:
               attachment = MIMEText(fsend.read(), _subtype=subtype)
        elif maintype == "image":
            with open(file_to_send, "rb") as fsend:
               attachment = MIMEImage(fsend.read(), _subtype=subtype)
        elif maintype == "audio":
            with open(file_to_send, "rb") as fsend:
               attachment = MIMEAudio(fsend.read(), _subtype=subtype)
        else:
            with open(file_to_send, "rb") as fsend:
               attachment = MIMEBase(maintype, subtype)
               attachment.set_payload(fsend.read())

        encoders.encode_base64(attachment)
        attachment.add_header("Content-Disposition", "attachment", filename=os.path.basename(file_to_send))
        msg.attach(attachment)

        try:
            conn = SMTP(server,timeout=int(self.timeout))
            conn.set_debuglevel(False)
            conn.login(self.mail_from, self.mail_pass)
            try:
                conn.sendmail('{}<{}>'.format('crawler',self.mail_from),self.mail_destination, msg.as_string())
                logging.info(" sent email from  {} to {}".format(self.mail_from,self.mail_destination))
            finally:
                conn.quit()
        except Exception as exc:
                logging.error("Error sent email: {} ".format(str(exc)))



class Storekeeper(MailWorker):

    def __init__(self, store_dir,loop, smtp_dict):
        self.__posts_saved = 0
        self.__comments_links_saved = 0
        self.store_dir = store_dir
        self.loop =  loop
        super().__init__(smtp_dict)

    def create_dirs(self, path):
        dirpath = os.path.dirname(path)
        os.makedirs(dirpath, exist_ok=True)

    def get_path(self, link_id, post_id, url):
        file_ext = "pdf"
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


    async def get_body(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                        return await response.read()
        except aiohttp.ClientError as ex:
            logging.error("aiohttp can't read response: %s" % ex)


    async def pdf_converter(self, url, post_id, link_id):
        """Run command in subprocess (shell)"""
        try:
            filepath = self.get_path(link_id, post_id, url)
            self.create_dirs(filepath)
            options = '--load-error-handling ignore --load-media-error-handling ignore'
            command = "wkhtmltopdf {}  '{}' {}".format(options, url, filepath)
            # Create subprocess
            process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE)
            logging.info('Coverter start: {}'.format(command))

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logging.info('Converter done: {} '.format(command))
                '''sending email'''
                print('send+++++++++++++++')
                self.attach_send('test',filepath)
            else:
                logging.info('Failed to convert: {}'.format(str(stderr)))
        except Exception as ex:
            logging.error("save err: {}".format(str(ex)))


async def get_links_from_comments(post_id, storekeeper):
    """
    Fetch comments page and parse links from comments
    """
    url = YCOMB_TEMPLATE.format(id = post_id)
    links = set()
    try:
        html = await storekeeper.get_body(url)
        soup = BeautifulSoup(html, "html5lib")
        for link in soup.select(".comment a[rel=nofollow]"):
            _url = link.attrs["href"]
            parsed_url = urlparse(_url)
            if parsed_url.scheme and parsed_url.netloc:
                #print(_url)
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
            descr = tr.select_one("td.title a.storylink").text
            if any(word in descr.lower() for word in FILTERS):
                print(descr)
                posts[id] = {'url':url,'descr':descr}
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
        links = [url['url']] + comments_links
        converter_tasks = [
            storekeeper.pdf_converter(link, post_id, ind) for ind, link in enumerate(links)
        ]
        await asyncio.gather(*converter_tasks)


async def monitor(storekeeper, queue, sleeptimer):
    """
    Periodically check news.ycombinator.com for new articles.
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
        await asyncio.sleep(sleeptimer)
        iteration += 1

def main(args):
    loop = asyncio.get_event_loop()
    storekeeper = Storekeeper(args.storedir, loop, SMTP_DICT)
    queue = asyncio.Queue(loop=loop)
    workers = [crawler(storekeeper, queue)]
    workers.append(monitor(storekeeper, queue,WAIT_AFTER_RETRY))
    loop.run_until_complete(asyncio.gather(*workers))
    loop.close()



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



