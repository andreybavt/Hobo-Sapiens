import asyncio
import io
import logging
from pathlib import Path

import diskcache as dc
import imagehash
from PIL import Image
from tornado.httpclient import HTTPRequest

from crawler_utils.async_proxy import AsyncProxyClient
from crawler_utils.utils import nofail_async


class ImageManager:
    logger = logging.getLogger(__name__)

    def __init__(self, storage_path=Path.home().joinpath('.hobo-sapiens', 'image-hashes')) -> None:
        super().__init__()
        self.image_hashes = dc.Cache(str(storage_path))

        self.client = AsyncProxyClient(monitoring=True)

    @nofail_async(retries=5, failback_result=(None, None))
    async def get_image_hash(self, image_url):
        res = await self.client.fetch(HTTPRequest(method='GET', url=image_url), use_proxy_for_request=False)
        image = Image.open(io.BytesIO(res.body))
        return image_url, str(imagehash.average_hash(image))

    def check_all(self, notification, urls):
        output = {}
        seen_in_messages = []
        loop = asyncio.get_event_loop()
        for url in urls:
            _, img_hash = loop.run_until_complete(self.get_image_hash(url))
            if img_hash not in self.image_hashes:
                self.image_hashes[img_hash] = {"hash": img_hash, "notif": notification}
                output[url] = self.image_hashes[img_hash]
            else:
                seen_in_messages.append(self.image_hashes[img_hash])
        return output, seen_in_messages

    def set_message_ids(self, hashes, message_id):
        for h in hashes:
            existing = self.image_hashes[h]
            existing['message_id'] = message_id
            self.image_hashes[h] = existing
