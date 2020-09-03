import asyncio
import math
from urllib.parse import urlencode

from tornado.httpclient import HTTPRequest

from crawler_utils.utils import read_prop
from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService


class LogicImmo(AbstractService):
    header = {
        'User-Agent': 'logicimmo-android/8.5.1',
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip'
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        with self.METRICS_INIT_TIME.time():
            self.locality_codes = asyncio.get_event_loop().run_until_complete(self.search_localities())

    def get_candidate_native_id(self, candidate) -> str:
        return candidate['identifiers']['reference']

    async def candidate_to_notification(self, c):
        if self.filter.furnished and not read_prop(c, 'properties', 'furnished'):
            return None

        return Notification(
            price=c['pricing']['amount'],
            location=c['location']['city']['postCode'],
            area=c['properties']['area'],
            url=c['info']['link'],
            pics_urls=[i.replace('width=[WIDTH]&height=[HEIGHT]&scale=[SCALE]', 'width=800&height=600&scale=1') for i in
                       c['pictures']],
            description=read_prop(c,'info','text').strip(),
            rooms=read_prop(c,'properties','rooms')
        )

    async def run(self):
        nb_pages = await self.do_for_page()
        for p in range(1, nb_pages):
            await self.do_for_page(p)

    async def do_for_page(self, page=0):
        items_per_page = 20

        data = {'area_range': f'{self.filter.min_area},',
                'client': 'v8.a.3',
                'domain': 'rentals',
                'limit': items_per_page,
                'localities': ','.join(self.locality_codes),
                'order': 'date-asc',
                'price_range': f'0,{self.filter.max_price}',
                'property_types': '1, 2, 6, 16, 30',
                'start': page * items_per_page}
        res = await self.client.patient_fetch(
            HTTPRequest("http://lisemobile.logic-immo.com/li.search_ads.php?" + urlencode(data)))
        res_json = res.json()
        for c in res_json['items']:
            await self.push_candidate(c)
        return math.ceil(res_json['search']['total'] / items_per_page)

    async def search_localities(self):
        payload = lambda x: {
            'client': "v8.a",
            'fulltext': x
        }
        resp, _ = await asyncio.wait([
            self.client.patient_fetch(
                HTTPRequest(url="http://lisemobile.logic-immo.com/li.search_localities.php?" + urlencode(payload(i))))
            for i in self.filter.arrondissements
        ])
        return [[i for i in r.result().json().get('items') if i['level'] == 2][0]['key'] for r in resp]

if __name__ == '__main__':
    f = Filter(arrondissements=[75003], max_price=2000, min_area=25, furnished=True)
    service = LogicImmo(f, False)
    asyncio.get_event_loop().run_until_complete(service.run())

