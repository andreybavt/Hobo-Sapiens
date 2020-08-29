import asyncio
import logging
import math
from urllib.parse import urlencode

from tornado.httpclient import HTTPRequest

from crawler_utils.utils import chunks, read_prop
from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService

ANNOUNCES_PER_PAGE = 16


class Laforet(AbstractService):

    def get_candidate_native_id(self, candidate):
        return candidate.get('immo_id')

    async def candidate_to_notification(self, c) -> Notification:
        return Notification(
            area=read_prop(c, 'surface'),
            location=read_prop(c, 'address', 'postcode'),
            price=read_prop(c, 'price'),
            url=read_prop(c, 'links', 'self'),
            pics_urls=read_prop(c, 'photos')
        )

    async def run(self):
        for chunk in chunks(self.filter.arrondissements, 7):
            await self.run_for_arrondissements(chunk)

    async def run_for_arrondissements(self, arrs):
        cities = ','.join([str(int(i) + 100) for i in arrs])
        nb_announces_params = {'cities': cities,
                               'max': self.filter.max_price, 'surface': self.filter.min_area, 'transaction': 'rent'}

        main_params = lambda x: {'cities': cities,
                                 'max': self.filter.max_price,
                                 'page': x,
                                 'perPage': ANNOUNCES_PER_PAGE,
                                 'surface': self.filter.min_area,
                                 'transaction': 'rent'}

        count_res = await self.client.patient_fetch(HTTPRequest(method='GET',
                                                                url='https://www.laforet.com/api/immo/properties/count?' + urlencode(
                                                                    nb_announces_params)), connect_timeout=2,
                                                    request_timeout=6)
        total_count = count_res.json()['count']

        for page in range(1, math.ceil(total_count / ANNOUNCES_PER_PAGE) + 1):
            search_base_url = 'https://www.laforet.com/api/immo/properties?'

            current_url = search_base_url + urlencode(main_params(page))
            get = await self.client.patient_fetch(HTTPRequest(method='GET', url=current_url),
                                                  connect_timeout=2, request_timeout=6)
            for c in get.json()['data']:
                await self.push_candidate(c)


if __name__ == '__main__':
    laforet = Laforet(Filter(arrondissements=[75018], max_price=2000, min_area=27))
    asyncio.get_event_loop().run_until_complete(laforet.run())
