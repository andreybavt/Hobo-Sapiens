import asyncio
import json
import math
import os

import aiohttp

from crawler_utils.utils import read_prop
from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService


class MoteurImmo(AbstractService):
    headers = {
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36',
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referer': 'https://moteurimmo.fr/',
    }
    per_page = 20

    moteurimmo_token_host = os.environ.get('HS_MOTEURIMMO_TOKEN_HOST', 'localhost')
    moteurimmo_token_port = os.environ.get('HS_MOTEURIMMO_TOKEN_PORT', '18081')

    def __init__(self, *args, **kwargs) -> None:
        self.session = aiohttp.ClientSession()  # Maybe migrate to aiohttp?
        with self.METRICS_INIT_TIME.labels(self.get_service_name()).time():
            asyncio.get_event_loop().run_until_complete(self.init_cookies())
        super().__init__(*args, *kwargs)

    def get_candidate_native_id(self, candidate) -> str:
        return candidate['_id']

    async def candidate_to_notification(self, c):
        if not c.get('pictureUrl'):
            return None
        return Notification(price=c.get('price'),
                            location=read_prop(c, 'location', 'postalCode'),
                            area=c.get('surface'),
                            url=c.get('url'),
                            pics_urls=[c.get('pictureUrl')])

    async def run(self):
        total_results = await self.run_for_page()
        for page in range(2, math.ceil(total_results / self.per_page) + 1):
            await self.run_for_page(page)

    async def run_for_page(self, page=1):
        data = {"types": [2], "categories": [1, 2], "sellerTypes": [1, 2], "sortBy": "publicationDate-desc",
                "priceMin": "", "priceMax": self.filter.max_price, "pricePerSquareMeterMin": "",
                "pricePerSquareMeterMax": "",
                "surfaceMin": self.filter.min_area, "surfaceMax": "", "landSurfaceMin": "", "landSurfaceMax": "",
                "roomsMin": "",
                "roomsMax": "", "bedroomsMin": "", "bedroomsMax": "", "locations": self.translated_locations,
                "radius": "", "constructionYearMin": "", "constructionYearMax": "",
                "floorMin": "", "floorMax": "", "buildingFloorsMin": "", "buildingFloorsMax": "",
                "extra": {"isFurnished": True} if self.filter.furnished else {},
                "keywords": [], "keywordsOperator": 1, "maxLength": self.per_page, "page": page}
        resp = await self.session.post(f"http://{self.moteurimmo_token_host}:{self.moteurimmo_token_port}", data=json.dumps(data))
        data['token'] = await resp.text()
        resp = await self.session.post("https://moteurimmo.fr/search/ads", json=data)
        resp = await resp.json()
        for c in resp['ads']:
            await self.push_candidate(c)
        return resp['count']

    async def translate_location(self, loc):
        res = await self.session.get(f'https://moteurimmo.fr/search/location?value={loc}')
        res = await res.json()
        return [i['value'] for i in res if 'postalCode' in i['value']][0]

    async def init_cookies(self):
        self.session.cookie_jar.clear()
        await self.session.post("https://moteurimmo.fr/user", headers=self.headers)


if __name__ == '__main__':
    f = Filter(arrondissements=[75001, 75002, 75003], max_price=1300, min_area=25)
    service = MoteurImmo(f, False)
    asyncio.get_event_loop().run_until_complete(service.run())
