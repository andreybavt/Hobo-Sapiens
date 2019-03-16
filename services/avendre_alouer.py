import asyncio
import math

import json
import logging
from datetime import datetime, timedelta
from tornado.httpclient import HTTPRequest
from urllib.parse import urlencode

from crawler_utils.utils import get_tasks_results, read_prop
from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService


class AvendreAlouer(AbstractService):

    def __init__(self, f: Filter, with_proxy=None) -> None:
        super().__init__(f, with_proxy)
        self.fetch_size = 100

        location_url = "https://ws-web.avendrealouer.fr/ref/localities/_autocomplete?term="
        self.auth_header = {"Authorization": "Basic ed9650a3:cc0d1854ffa93628166452d2258ec162"}
        res = get_tasks_results(asyncio.get_event_loop().run_until_complete(asyncio.wait(
            [self.client.patient_fetch(HTTPRequest(method="GET", url=location_url + str(i), headers=self.auth_header))
             for i in self.filter.arrondissements])), is_json=True)
        self.locality_ids = ','.join([i['items'][0]['id'] for i in res])

    def get_candidate_native_id(self, candidate) -> str:
        return candidate['id']

    async def candidate_to_notification(self, c) -> Notification:
        return Notification(
            price=c['price'],
            location=read_prop(c, 'viewData', 'localityName'),
            area=c['surface'],
            url=f"https://www.avendrealouer.fr/{c['realms']['aval']['url']}",
            pics_urls=[i['url'] for i in c['medias']['photos']]) if read_prop(c, 'medias', 'photos') else []

    async def run(self):
        first_page = await self.fetch_page()
        for i in first_page['items']:
            await self.push_candidate(i)
        nb_pages = math.ceil(first_page['count'] / self.fetch_size)
        if nb_pages > 1:
            for r in (await asyncio.wait([self.fetch_page(i) for i in range(2, nb_pages + 1)]))[0]:
                for i in r.result()['items']:
                    await self.push_candidate(i)

    async def fetch_page(self, page=1):
        querystring = {"price.lte": self.filter.max_price, "surface.gte": self.filter.min_area,
                       "localityIds": self.locality_ids,
                       "size": self.fetch_size,
                       "from": (page - 1) * self.fetch_size,
                       "releaseDate.gte": (datetime.today() - timedelta(days=3)
                                           ).strftime("%Y-%m-%d")}
        if self.filter.furnished:
            querystring["housingIds"] = 1
        res = await self.client.patient_fetch(HTTPRequest(
            method="GET",
            headers=self.auth_header,
            url="https://ws-web.avendrealouer.fr/realestate/properties?" + urlencode(querystring, safe=',')))
        return json.loads(res.body.decode())


if __name__ == '__main__':
    f = Filter(arrondissements=[75001, 75002, 75003, 75004, 75005, 75010, 75011, 75008, 75009], max_price=13000,
               min_area=25)
    service = AvendreAlouer(f, False)
    asyncio.get_event_loop().run_until_complete(service.run())
    logging.info(len(service.notifications))
