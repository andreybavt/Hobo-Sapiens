import asyncio

import imagehash
import io
import shelve
from PIL import Image
from tornado.httpclient import HTTPRequest

from crawler_utils.async_proxy import AsyncProxyClient
from crawler_utils.utils import nofail_async


class ImageManager:
    def __init__(self) -> None:
        super().__init__()
        self.image_hashes = shelve.open('image_hashes')
        self.client = AsyncProxyClient()

    @nofail_async(retries=5, failback_result=(None, None))
    async def get_image_hash(self, image_url):
        res = await self.client.fetch(HTTPRequest(method='GET', url=image_url), use_proxy_for_request=False)
        image = Image.open(io.BytesIO(res.body))
        return image_url, imagehash.average_hash(image)

    def check_all(self, notification, urls):
        output = {}
        seen_in_messages = []
        res = asyncio.get_event_loop().run_until_complete(asyncio.wait([
            self.get_image_hash(i) for i in urls
        ]))
        for url, hash in [r.result() for r in res[0] if res[0]]:
            hash_str = str(hash)
            if hash_str not in self.image_hashes:
                self.image_hashes[hash_str] = {"hash": hash_str, "notif": notification}
                output[url] = self.image_hashes[hash_str]
            else:
                seen_in_messages.append(self.image_hashes[hash_str])
        return output, seen_in_messages

    def set_message_ids(self, hashes, message_id):
        for h in hashes:
            existing = self.image_hashes[h]
            existing['message_id'] = message_id
            self.image_hashes[h] = existing
