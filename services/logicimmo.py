import asyncio

import json
import logging
import re
from bs4 import BeautifulSoup
from tornado.httpclient import HTTPRequest

from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService
from services.service_utils import only_digits


class LogicImmo(AbstractService):

    def __init__(self, f: Filter, with_proxy=None) -> None:
        super().__init__(f, with_proxy)
        res = asyncio.get_event_loop().run_until_complete(self.client.patient_fetch(
            HTTPRequest(url="https://www.logic-immo.com/asset/t9/getLocalityT9.php?site=fr&lang=fr&json=%22750%22")))
        arr_data = [i for i in json.loads(res.body.decode()) if i['name'] == 'Ville(s)'][0]['children']
        self.arrs = {a['lct_post_code']: a for a in arr_data}

    def get_candidate_native_id(self, candidate) -> str:
        return candidate.id

    async def candidate_to_notification(self, c: Notification) -> Notification:
        res = await self.client.patient_fetch(HTTPRequest(url=c.url))
        soup = BeautifulSoup(res.body.decode(), 'lxml')

        c.location = re.search(r'\((.*?)\)', soup.select_one('[itemprop="address"]').text).group(1)
        c.price = only_digits(soup.select_one('.main-price').text)
        c.area = soup.select_one('.offer-area-number').text
        c.pics_urls = list({e.get('src').replace('75x75','800x600') for e in soup.select('#gallery  a > img')})
        return c

    async def run(self):
        nb_pages = await self.do_for_page()
        for p in range(2, nb_pages + 1):
            await self.do_for_page(p)

    async def do_for_page(self, page=1):
        arr_url_part_1 = ','.join([self.arrs[str(a)].get('lct_name').replace(' ', '-').lower() + "-" + str(a) for a in
                                   self.filter.arrondissements])
        arr_url_part_2 = ','.join([self.arrs[str(a)].get('lct_id') + "_2" for a in
                                   self.filter.arrondissements])

        furnished_url_part = "/searchoptions=4" if self.filter.furnished else ""
        # url = f"https://www.logic-immo.com/location-immobilier-{arr_url_part_1},{arr_url_part_2}/options/groupprptypesids=1,2,6,7,12/page={page}{furnished_url_part}/pricemax={self.filter.max_price}/areamin={self.filter.min_area}"
        url = f"https://www.logic-immo.com/location-immobilier/options/grouplocalities={arr_url_part_2}/groupprptypesids=1,2,6,7,12{furnished_url_part}/pricemax={self.filter.max_price}/areamin={self.filter.min_area}"
        rest = await self.client.patient_fetch(HTTPRequest(url=url))
        soup = BeautifulSoup(rest.body.decode(), 'lxml')
        paginator_els = soup.select('.offer-pagination-wrapper div.numbers a')
        nb_pages = int(paginator_els[-1].text) if len(paginator_els) else 1
        candidates = []
        for u in {e.get('href') for e in soup.select('.offer-list-content a') if 'detail-' in e.get('href')}:
            candidates.append(Notification(id=u[-40:-4], url=u))
        if len(candidates):
            await asyncio.wait([self.push_candidate(c) for c in candidates])
        return nb_pages


if __name__ == '__main__':
    f = Filter(arrondissements=[75001, 75002, 75003], max_price=10000, min_area=25)
    service = LogicImmo(f, False)
    asyncio.get_event_loop().run_until_complete(service.run())
    logging.info(service.notifications)
