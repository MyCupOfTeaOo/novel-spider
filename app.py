import os
from download import BiQuGeDownload
import asyncio
import logging
from colorama import init
from termcolor import colored
import re
import argparse


_suffix = re.compile('\n$')

LOG_FORMAT = "%(asctime)s %(name)s-%(levelname)s(%(filename)s:%(funcName)s): %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

DOWNLOAD_MAP = {
    "biquge": BiQuGeDownload
}


class QueueHandler(logging.Handler):

    def emit(self, record):
        if not record.getMessage() or record.getMessage() == '\n' or record.getMessage() == '\r\n':
            return
        if(record.levelname == 'ERROR'):
            print(colored(_suffix.sub('', self.format(record), 1), 'red'))
        elif (record.levelname == 'INFO'):
            print(colored(_suffix.sub('', self.format(record), 1), 'green'))
        elif (record.levelname == 'WARNING'):
            print(colored(_suffix.sub('', self.format(record), 1), 'yellow'))
        else:
            print(colored(_suffix.sub('', self.format(record), 1), 'cyan'))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("name", help="下载后的文件名,文件会下载到files下")
    parser.add_argument("url", help="目录链接")
    parser.add_argument("-p", "--process",
                        help="下载进程数,默认5", type=int, default=5)
    parser.add_argument("--proxy",
                        help="代理地址,默认http://127.0.0.1:1080", default='http://127.0.0.1:1080')
    parser.add_argument("--download", default="biquge",
                        help="下载器设置, 目前只支持 biquge(笔趣阁)")

    args = parser.parse_args()

    cust_handler = QueueHandler()
    cust_handler.setFormatter(logging.Formatter(
        datefmt=DATE_FORMAT, fmt=LOG_FORMAT))
    logging.basicConfig(level=logging.DEBUG, handlers=(
        cust_handler,))
    init()
    TargetDownLoad = DOWNLOAD_MAP[args.download.lower()]
    down = TargetDownLoad(args.name,
                          args.url, proxy=args.proxy if args.proxy else None, process_num=args.process)
    asyncio.run(down.go())
    logging.info(f"输出文件: {' '.join(args.name)}")
    down.output()
    logging.info(f'{args.name}\t下载完毕')
