import asyncio
import math

import json
import logging
import urllib
from tornado.httpclient import HTTPRequest

from crawler_utils.utils import read_prop
from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService


class LouerVite(AbstractService):

    def __init__(self, f: Filter, with_proxy=None) -> None:
        self.page_size = 100
        super().__init__(f, with_proxy)

    def get_candidate_native_id(self, c) -> str:
        return c['IdAnnonce']

    async def candidate_to_notification(self, c) -> Notification:
        return Notification(price=c['Prix'],
                            location=c['CodePostal'],
                            area=c['Surface'],
                            url=f"https://www.louervite.fr/{c['Url']}",
                            pics_urls=[v['Formats'][-1]['Url'] for v in c['Visuels']])

    async def run(self):
        first_data, total_els = await self.get_results_from_page()
        if not len(first_data):
            return
        for e in first_data:
            await self.push_candidate(e)
        total_pages = math.ceil(total_els / self.page_size)
        if total_pages > 1:
            res = (await asyncio.wait([self.get_results_from_page(p) for p in range(2, total_pages + 1)]))[0]
            results = [e for r in res for e in r.result()[0]]
            for r in results:
                await self.push_candidate(r)

    async def get_results_from_page(self, page=1):

        url = "https://ws.louervite.fr/AnnonceWebService.svc/RechercherAnnonces"
        data = {"Criteres": {"CodesInsee": [f"7501{str(a)[-2:]}" for a in self.filter.arrondissements],
                             "Tri": {"Parameter": "DateCreation", "Asc": 'false'},
                             "Pagination": {"PageIndex": page - 1, "PageSize": self.page_size},
                             "TypesBien": [1],
                             "NbPiecesMin": 1,
                             "SurfaceMin": self.filter.min_area,
                             "PrixMin": 100, "PrixMax": self.filter.max_price,
                             "EstDerniereRecherche": 'false',
                             "EstRechercheRefine": 'true'}}
        if self.filter.furnished == True:
            data['Criteres']["Meuble"] = 'true'
        if self.filter.furnished == False:
            data['Criteres']["NonMeuble"] = 'true'
        headers = {
            'Accept': "application/json, text/javascript, */*; q=0.01",
            'Content-Type': "application/x-www-form-urlencoded; charset=UTF-8",
            'cache-control': "no-cache"
        }
        response = await self.client.patient_fetch(
            HTTPRequest(method="GET", url=url + '?request=' + urllib.parse.quote(json.dumps(data)), headers=headers))
        resp_data = json.loads(response.body.decode())
        nb_results = read_prop(resp_data, 'd', 'Data', 'Resultats', 'TotalResults')
        results = read_prop(resp_data, 'd', 'Data', 'Resultats', 'Resultats')
        return results, nb_results


if __name__ == '__main__':
    f = Filter(arrondissements=[75001, 75002, 75012], max_price=13000, min_area=25)
    service = LouerVite(f, False)
    asyncio.get_event_loop().run_until_complete(service.run())
    logging.info(service.notifications)
