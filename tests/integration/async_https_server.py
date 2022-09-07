#! /usr/bin/env python3

# SPDX-FileCopyrightText: 2022 The Tor Project, Inc.
#
# SPDX-License-Identifier: BSD-3-Clause

import argparse
import logging
import os
import random
import ssl
import time

from aiohttp import hdrs, web

HERE_PATH = os.path.dirname(os.path.abspath(__file__))
CERT_PATH = os.path.join(HERE_PATH, "data")
RESPONSE_HEADERS = {"Content-Type": "application/octet-stream"}
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
print(logger.__dict__)


async def handle(request):
    logger.debug("Request headers: %s.", request.headers)
    if request.method == "GET":
        logger.info("GET request with http_range: %s.", request.http_range)
        if (
            request.http_range.start is not None
            and request.http_range.stop is not None
        ):
            length = request.http_range.stop - request.http_range.start
            # From python 3.9 replace by random.randbytes.
            random_bytes = bytes(
                [random.randrange(0, 256) for _ in range(0, length)]
            )
            return web.Response(
                body=random_bytes, content_type="application/octet-stream"
            )
        return web.Response(body=None, content_type="application/octet-stream")
    if request.method == "HEAD":
        logger.info("HEAD request.")
        return web.Response(
            body=None,
            content_type="application/octet-stream",
            headers={"Content-Length": str(1024**3)},
        )
    if request.method == "POST":
        logger.debug("Method POST")
        return await handle_post_multipart(request)


async def handle_post_multipart(request):
    """

    Examples:
    1. HTTP POST via Content-Type multipart/form-data RFC 2388 as a file
       upload::

            curl -F "data=@20Mb.zero" https://localhost:28888 -O

       Server receive headers::

            'Host': 'localhost:28888',
            'User-Agent': 'curl/7.74.0',
            'Accept': '*/*',
            'Content-Length': '20971730',
            'Content-Type': 'multipart/form-data;
                boundary=------------------------b194991f7a742a17',

        And reading data server receives headers::

        'Content-Disposition': 'form-data; name="data"; filename="20Mb.zero"',
        'Content-Type': 'application/octet-stream',
        '_boundary': b'--------------------------b194991f7a742a17',
        '_content': <StreamReader 81758 bytes>,

    2. HTTP POST via Content-Type multipart/form-data RFC 2388 as a raw (text)
       field upload::
            curl -F "data=<20Mb.zero" https://localhost:28888 -O

       Server receives headers::

        'Host': 'localhost:28888',
        'User-Agent': 'curl/7.74.0',
        'Accept': '*/*',
        'Content-Length': '20971663',
        'Content-Type': 'multipart/form-data;
            boundary=------------------------48c320a9e28750c6',
        'Expect': '100-continue'

        And reading data server receives headers::

        'Content-Disposition': 'form-data; name="data"',
        '_boundary': b'--------------------------48c320a9e28750c6',
        '_content': <StreamReader 81825 bytes>,

    3. HTTP POST as HTTP MQTT binary::

            curl -k --data-binary "@20Mb.zero" https://localhost:28888/post -O

       It raises: ``multipart/* content type expected``.

    """
    name = ""
    try:
        reader = await request.multipart()
        logger.debug("reader %s", reader.__dict__)
        expected_size = reader.headers.get(hdrs.CONTENT_LENGTH, None)
        logger.debug("expected size %s", expected_size)
        expected_type = reader.headers.get(hdrs.CONTENT_TYPE, None)
        logger.debug("expected type %s", expected_type)
        size = 0
        while True:
            logger.debug("next")
            part = await reader.next()
            if part is None:
                break
            logger.debug("part %s", part.__dict__)
            filename = part.filename
            logger.debug("filename: %s", filename)
            name = part.name
            logger.debug("name %s", name)
            # logger.debug(part.__dict__)
            start = time.monotonic()
            filedata = await part.read(decode=False)
            end = time.monotonic()
            logger.debug("part.read %s", end - start)
            size += len(filedata)
            logger.debug("size filedata %s", size)
    except Exception as ex:
        logger.warning("Wrong multipart request: %s", ex)
        return web.Response(status=400)
    logger.debug("finished")
    return web.Response(
        text="successfully uploaded {} sized of {}\n" "".format(name, size)
    )


def main():
    parser = argparse.ArgumentParser(description="aiohttp server example")
    parser.add_argument("-l", "--host", default="127.0.0.1")
    parser.add_argument("-p", "--port", default=28888)
    parser.add_argument(
        "-k", "--certkey", default=os.path.join(CERT_PATH, "localhost.key")
    )
    parser.add_argument(
        "-c", "--certfile", default=os.path.join(CERT_PATH, "localhost.crt")
    )
    args = parser.parse_args()

    app = web.Application()
    app.add_routes(
        [
            web.get("/", handle),
            web.post("/", handle),
        ]
    )

    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(args.certfile, args.certkey)

    web.run_app(app, host=args.host, port=args.port, ssl_context=ssl_context)


if __name__ == "__main__":
    main()
