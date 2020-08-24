import asyncio

import json
import logging
from bs4 import BeautifulSoup
from tornado.httpclient import HTTPRequest
from urllib.parse import urlencode

from crawler_utils.utils import read_prop
from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService
from services.service_utils import only_digits


class ChunkReader:

    def __init__(self) -> None:
        super().__init__()
        self.content = ""

    def read(self, chunk):
        self.content = self.content + chunk.decode()


class MeilleursAgents(AbstractService):

    def __init__(self, f: Filter, enable_proxy=None) -> None:
        super().__init__(f, enable_proxy)
        geo = asyncio.get_event_loop().run_until_complete(self.client.patient_fetch(
            HTTPRequest(url="https://geo.meilleursagents.com/geo/v1/?q=750&types=subregions,cities,arrmuns")))
        self.zip_map = {i['zip']: i for i in read_prop(json.loads(geo.body.decode()), 'response', 'places')}
        self.arr_to_zip = {i['name_short']: i['zip'] for i in self.zip_map.values()}

    def get_candidate_native_id(self, candidate) -> str:
        return candidate.id

    async def candidate_to_notification(self, c: Notification) -> Notification:
        reader = ChunkReader()
        res = await self.client.patient_fetch(HTTPRequest(url=c.url, headers={
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}))
        html = BeautifulSoup(res.body.decode(), 'lxml')
        c.pics_urls = [f"http:{i['href']}" for i in html.select('.listing-slideshow__link')]
        return c

    async def run(self):
        total_pages = await self.run_for_page()
        for i in range(2, total_pages + 1):
            await self.run_for_page(i)

    async def run_for_page(self, page=1):
        url = "https://www.meilleursagents.com/annonces/location/search/"
        params = {
            "transaction_types": "TRANSACTION_TYPE.RENT",
            "place_ids": ','.join([self.zip_map[str(a)]['id'] for a in self.filter.arrondissements]),
            "item_types": "ITEM_TYPE.APARTMENT,ITEM_TYPE.HOUSE",
            "max_price": str(self.filter.max_price),
            "min_area": str(self.filter.min_area),
            "page": str(page)
        }
        params_encoded = urlencode(params, safe=',')
        res = await self.client.patient_fetch(HTTPRequest(url=f"{url}?{params_encoded}"))
        import requests
        res_sync = requests.get(f"{url}?{params_encoded}")
        soup = BeautifulSoup(json.loads(res.body.decode())['html'], 'lxml')
        if soup.select('.pagination__page'):
            total_pages = int(soup.select('.pagination__page')[-1]['data-paginate-page-num'])
        else:
            total_pages = 1

        async def push_candidate_el(e):
            href = e.select_one('a')['href']
            await self.push_candidate(Notification(
                id=e.select_one('.listing-actions__item')['data-listing-id'],
                price=only_digits(e.select_one('.listing-price').text.strip()),
                url=href,
                location=self.arr_to_zip[e.select_one('[data-search-listing-item-place]').text],
                area=only_digits(e.select_one('.listing-caracteristic').text.strip().split('-')[-1])
            ))

        await asyncio.wait([push_candidate_el(e) for e in soup.select('.listing-item.search-listing-result__item')])

        return total_pages


if __name__ == '__main__':
    f = Filter(arrondissements=[75001, 75002, 75003, 75011], max_price=1300, min_area=25)
    service = MeilleursAgents(f, False)
    asyncio.get_event_loop().run_until_complete(service.run())

