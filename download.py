import re
import traceback
from typing import List
import aiohttp
import asyncio
import os
import logging
import aiofiles
import signal
import json
from bs4 import BeautifulSoup
import shutil
from urllib.parse import urljoin

TIMEOUT = 20


def get_user_agent():
    # ua = UserAgent()
    # return ua.random
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36"


class Download():
    _list_url = ""
    _uid_list: List[str] = []
    _downloading_uid: List[str] = []
    _wait_down_uid: List[str] = []
    _error_count = 0
    _consecutive_error_count = 0

    def __init__(self, name, list_url, proxy=None, process_num=10):
        self._list_url = list_url
        self._proxy = proxy
        self.process_num = process_num
        self._name = name
        self._path = f'files/{name}'

    async def go(self):
        signal.signal(signal.SIGTERM, self.registry_exit_callback)
        signal.signal(signal.SIGINT, self.registry_exit_callback)
        asyncio.ensure_future(self.monitor())
        if os.path.exists(f'{self._path}/log.json'):
            logging.debug(f'检测到历史下载记录,重新构建队列')
            await self.refactor_list()
        else:
            await self.init_list()

    async def monitor(self):
        logging.info(f'总共:\t {len(self._uid_list)}')
        logging.info(
            f'已下载:\t {len(self._uid_list) - len(self._wait_down_uid)}')
        logging.info(f'待下载:\t {len(self._wait_down_uid)}')
        logging.info(f'正在下载:\t {len(self._downloading_uid)}')
        logging.info(f'失败次数:\t {self._error_count}')
        if (self._consecutive_error_count > 20):
            logging.error("连续下载失败过多,退出程序")
            self.registry_exit_callback(1, 1)
        await asyncio.sleep(5)
        asyncio.ensure_future(self.monitor())

    def registry_exit_callback(self, signum, frame):
        logging.debug('检测到退出信号,准备写日志')
        self.write_log()
        os._exit(0)

    def write_log(self):
        if not os.path.exists(self._path):
            os.makedirs(self._path)
        with open(f'{self._path}/log.json', "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "wait_urls": self._wait_down_uid + self._downloading_uid,
                "error_count": self._error_count,
                "_uid_list": self._uid_list,
            }, ensure_ascii=False,
                indent=2, separators=(',', ':')))

    async def refactor_list(self):
        headers = {'user-agent': get_user_agent()}
        async with aiohttp.ClientSession() as session:
            async with session.get(self._list_url, headers=headers, timeout=TIMEOUT, proxy=self._proxy, verify_ssl=False) as res:
                list_text = await res.text()
                if (res.status > 300):
                    logging.error(list_text)
                    os._exit(0)
                with open(f'{self._path}/log.json', encoding="utf-8", mode="r") as f:
                    log = json.loads(f.read())
                self._uid_list = log["_uid_list"]
                self._wait_down_uid = log["wait_urls"].copy()
                await asyncio.gather(*[self.uid_process() for i in range(self.process_num)])
                # 回写日志,防止重下载
                self.write_log()

    async def init_list(self):
        headers = {'user-agent': get_user_agent()}
        async with aiohttp.ClientSession() as session:
            async with session.get(self._list_url, headers=headers, timeout=TIMEOUT, proxy=self._proxy, verify_ssl=False) as res:
                list_text = await res.text()
                if (res.status > 300):
                    logging.error(list_text)
                    os._exit(0)
                self._uid_list = self.parse_list(
                    BeautifulSoup(list_text, "html.parser"))
                self._wait_down_uid = self._uid_list.copy()
                await asyncio.gather(*[self.uid_process() for i in range(self.process_num)])
                # 回写日志,防止重下载
                self.write_log()

    async def uid_process(self):
        while True:
            if len(self._wait_down_uid) < 1:
                return
            uid = self._wait_down_uid.pop(0)
            self._downloading_uid.append(uid)
            logging.debug(f'开始下载 {uid}')
            result = await self.pipe(uid)
            if result:
                self._consecutive_error_count = 0
                self._downloading_uid.remove(uid)
                logging.debug(f'{uid} 下载成功')
            else:
                logging.error(f'{uid} 下载失败')
                self._error_count += 1
                self._consecutive_error_count += 1
                self._wait_down_uid.append(uid)
                self._downloading_uid.remove(uid)

    async def pipe(self, uid):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(uid, timeout=TIMEOUT, proxy=self._proxy, verify_ssl=False) as res:
                    if res.status == 200:
                        text = await res.text()
                        html = BeautifulSoup(text, "html.parser")
                        title = self.parse_title(html)
                        article = self.parse_article(html)
                        await self.create_file(self._uid_list.index(uid), "%s\n%s\n" % (title.strip(), "\t\t%s" % article.strip()))
                        return True
        except:
            logging.error(traceback.format_exc())
            return False

    async def create_file(self, filename, text):
        if not os.path.exists(self._path):
            os.makedirs(self._path)
        filepath = f'{self._path}/{filename}.txt'
        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write(text)

    def output(self):
        filepath = f'{self._path}.txt'
        with open(filepath, "w", encoding="utf-8") as outFile:
            for i, _ in enumerate(self._uid_list):
                with open(f"{self._path}/{i}.txt", "r", encoding="utf-8") as inFile:
                    outFile.write(inFile.read())
        shutil.rmtree(self._path)
        
    def parse_list(self, html: BeautifulSoup) -> List[str]:
        print(html.prettify())
        raise NotImplementedError("not implemented error parse_list")

    def parse_title(self, html: BeautifulSoup) -> str:
        raise NotImplementedError("not implemented error parse_title")

    def parse_article(self, html: BeautifulSoup) -> str:
        raise NotImplementedError("not implemented error parse_article")


class BiQuGeDownload(Download):

    _replace_text = re.compile(r"请收藏本站[\w\W.]*?『加入书签』")

    def parse_list(self, html: BeautifulSoup) -> List[str]:
        elements = html.select_one(".listmain").select("a")
        links = map(lambda element: urljoin(
            self._list_url, element["href"]), filter(lambda element: not element["href"].startswith("javascript:"), elements))
        return list(links)

    def parse_title(self, html: BeautifulSoup) -> str:
        title = html.select_one(".content").select_one(".wap_none").text
        return title or "找不到标题"

    def parse_article(self, html: BeautifulSoup) -> str:
        article = html.select_one("#chaptercontent").getText("\n")
        article = self._replace_text.sub("", article)
        index = article.index("\n")
        article = article[index:]
        return article or "本章无文字"

    async def pipe(self, uid):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(uid, timeout=TIMEOUT, proxy=self._proxy, verify_ssl=False) as res:
                    if res.status == 200 or res.status == 503:
                        text = await res.text()
                        html = BeautifulSoup(text, "html.parser")
                        title = self.parse_title(html)
                        article = self.parse_article(html)
                        await self.create_file(self._uid_list.index(uid), "%s\n%s\n" % (title.strip(), "\t\t%s" % article.strip()))
                        return True
        except:
            logging.error(traceback.format_exc())
            return False
