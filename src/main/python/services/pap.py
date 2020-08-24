import asyncio
from typing import Optional
from urllib.parse import urlencode

from tornado.httpclient import HTTPRequest

from crawler_utils.utils import read_prop, chunks
from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService


class Pap(AbstractService):

    def get_service_name(self) -> str:
        return "Pap"

    def get_candidate_native_id(self, candidate):
        return candidate['id']

    async def candidate_to_notification(self, candidate) -> Optional[Notification]:
        candidate_location = self.paparr_to_arr(read_prop(candidate, '_embedded', 'place')[0]['id'])
        if candidate_location not in self.filter.arrondissements:
            return None
        det = await self.client.patient_fetch(HTTPRequest(method='GET', url=candidate['_links']['self']['href']))
        det = det.json()
        if not read_prop(det, '_embedded', 'photo'):
            return None
        return Notification(
            price=candidate['prix'],
            location=candidate_location,
            area=candidate['surface'],
            url=candidate['_links']['desktop']['href'],
            pics_urls=[i['_links']['self']['href'] for i in read_prop(det, '_embedded', 'photo')]
        )

    def arr_to_paparr(self, arr):
        return int(arr) - 75000 + 37767

    def paparr_to_arr(self, paparr):
        return int(paparr) - 37767 + 75000

    async def run(self):
        arr = [self.arr_to_paparr(i) for i in self.filter.arrondissements]

        data = {'recherche[geo][ids][]': arr,
                'recherche[prix][max]': self.filter.max_price,
                'recherche[produit]': 'location',
                'recherche[typesbien][]': ['maison','appartement'],
                'order': 'date-desc',
                'recherche[surface][min]': self.filter.min_area,
                'size': '200'}
        if self.filter.furnished:
            data['recherche[tags][]'] = 'meuble'

        url = 'https://ws.pap.fr/immobilier/annonces?' + urlencode(data, doseq=True)

        resp = await self.client.patient_fetch(HTTPRequest(method='GET', url=url))
        # 50 - not to go too far in history
        for chunk in chunks(resp.json()['_embedded']['annonce'][:50], 10):
            await asyncio.wait([self.push_candidate(c) for c in chunk])


if __name__ == '__main__':
    f = Filter(arrondissements=[75001, 75002, 75003, 75004],
               max_price=2000,
               min_area=25)
    service = Pap(f, True)
    res = asyncio.get_event_loop().run_until_complete(service.run())
    service.logger.info(res)
