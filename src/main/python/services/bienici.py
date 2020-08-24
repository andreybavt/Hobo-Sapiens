import asyncio
import json

from tornado.httpclient import HTTPRequest

from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService


class BienIci(AbstractService):

    def __init__(self, f: Filter, *args, **kwargs) -> None:
        super().__init__(f, *args, **kwargs)
        self.url = 'https://www.bienici.com/realEstateAds.json'

        arr_responses = asyncio.get_event_loop().run_until_complete(
            asyncio.wait([self.client.patient_fetch(
                HTTPRequest(method="GET", url='https://res.bienici.com/suggest.json?q=' + str(a))) for a in
                f.arrondissements]))
        self.filter_zones = [json.loads(i.result().body.decode())[0] for i in arr_responses[0]]

    def get_service_name(self) -> str:
        return "BienIci"

    def get_candidate_native_id(self, candidate):
        return candidate['id']

    async def candidate_to_notification(self, candidate) -> Notification:
        return Notification(price=candidate['price'],
                            location=candidate['postalCode'],
                            area=candidate['surfaceArea'],
                            url="https://www.bienici.com/annonce/location/" + self.get_candidate_native_id(candidate),
                            pics_urls=[p['url'] for p in candidate['photos']])

    async def run(self):
        zones = ','.join([i for z in self.filter_zones for i in z['zoneIds']])
        url = 'https://www.bienici.com/realEstateAds.json?' \
              'filters={"size":500,"from":0,"filterType":"rent","propertyType":["house","flat"],' \
              '"maxPrice":' + str(self.filter.max_price) + ',"minArea":' + str(self.filter.min_area) + \
              ',"page":1,"resultsPerPage":2400,"maxAuthorizedResults":2400,"sortBy":"relevance",' \
              '"sortOrder":"desc","onTheMarket":[true],"showAllModels":false,' \
              + ('"isFurnished":true,' if self.filter.furnished else '') + \
              '"zoneIdsByTypes":{"zoneIds":[' + zones + ']}}'

        resp = await self.client.patient_fetch(
            connect_timeout=60, request_timeout=60 * 2,
            request=HTTPRequest(method="GET", url=url),
        )
        resp = json.loads(resp.body.decode())
        for c in resp['realEstateAds']:
            await self.push_candidate(c)


if __name__ == '__main__':
    # , 75002, 75003, 75004, 75005, 75010, 75011, 75008, 75009
    f = Filter(arrondissements=[75010],
               max_price=1400,
               # furnished=True,
               min_area=35)

    service = BienIci(f, False)
    res = asyncio.get_event_loop().run_until_complete(service.run())
    service.logger.info(res)
