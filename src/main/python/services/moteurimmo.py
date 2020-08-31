import asyncio
import json
import math
import os
from http.cookies import SimpleCookie

from tornado.httpclient import HTTPRequest

from crawler_utils.utils import read_prop, nofail_async
from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService
from services.avendre_alouer import AvendreAlouer
from services.bienici import BienIci
from services.figaro import Figaro
from services.leboncoin import LeBonCoin
from services.logicimmo import LogicImmo
from services.pap import Pap
from services.seloger import Seloger


class MoteurImmo(AbstractService):
    cookies = {}
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

    def get_service_prefixed_id(self, pub):
        origin_mapping = {
            1: AvendreAlouer, #ok
            2: LeBonCoin, #ok
            3: LogicImmo,
            4: Pap, #ok
            5: Seloger,
            6: BienIci, #ok
            7: Figaro, #ok
            8: "ParuVendu",
            9: "Lesiteimmo",
            10: "AcheterLouer",
            11: "Vivastreet",
            12: "Kicherchekoi",
            13: "EtreProprio",
            14: "Immonot",
            15: "ImmoRegion",
            16: "OuestFrance",
            17: "MaisonsEtAppartements"
        }
        origin = origin_mapping.get(pub['origin'])
        if type(origin) == type:
            return f"{origin.get_service_name()}__{pub['adId']}"
        else:
            return f"{self.get_service_name()}__{self.get_candidate_native_id(pub)}"

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
        await self.init_cookies()
        total_results = await self.run_for_page()
        for page in range(2, math.ceil(total_results / self.per_page) + 1):
            await self.run_for_page(page)

    @nofail_async(retries=5, failback_result=[])
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

        resp = await self.client.fetch(
            HTTPRequest(method='POST', url=f"http://{self.moteurimmo_token_host}:{self.moteurimmo_token_port}",
                        body=json.dumps(data)), use_proxy_for_request=False)
        data['token'] = resp.body.decode()
        resp = await self.client.fetch(
            HTTPRequest(method="POST", url="https://moteurimmo.fr/search/ads",
                        body=json.dumps(data, ensure_ascii=False), headers=self.headers), cookies=self.cookies)
        resp = resp.json()
        for c in resp['ads']:
            await self.push_candidate(c)
        return resp['count']

    async def translate_location(self, loc):
        res = await self.client.fetch(
            HTTPRequest(url=f'https://moteurimmo.fr/search/location?value={loc}', method='GET', headers=self.headers),
            cookies=self.cookies)
        res = res.json()
        return [i['value'] for i in res if 'postalCode' in i['value']][0]

    async def post_client_init(self):
        await self.init_cookies()

    async def init_cookies(self):
        if 'Cookie' in self.headers:
            self.headers.pop('Cookie')
        res = await self.client.patient_fetch(HTTPRequest(url='https://moteurimmo.fr/user', headers=self.headers),
                                              ok_statuses=[401])
        if 'Set-Cookie' in res.headers:
            cookie = SimpleCookie()
            cookie.load(dict(res.headers)['Set-Cookie'])
            self.cookies = {key: value.value for key, value in cookie.items()}


if __name__ == '__main__':
    f = Filter(arrondissements=[75001], max_price=2300, min_area=25)
    service = MoteurImmo(f, True)
    asyncio.get_event_loop().run_until_complete(service.run())
