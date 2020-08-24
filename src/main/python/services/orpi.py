import asyncio
import json

from tornado.httpclient import HTTPRequest

from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService


class Orpi(AbstractService):
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'OrpiAroundMe/12 CFNetwork/978.0.7 Darwin/18.7.0',
        'Connection': 'keep-alive',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-us',
        'Authorization': 'AwesomeApiKeyForMobileApp85323664'
    }

    def __init__(self, f: Filter, enable_proxy=None) -> None:
        super().__init__(f, enable_proxy)
        self.locations = asyncio.get_event_loop().run_until_complete(self.search_locations())

    def get_candidate_native_id(self, candidate) -> str:
        return candidate['id']

    async def candidate_to_notification(self, c) -> Notification:
        return Notification(
            price=c['price'],
            area=c['surface'],
            location=c['locationDescription'],
            url=f"https://www.orpi.com/annonce-location-{c['slug']}",
            pics_urls=c.get('images')
        )

    async def run(self):
        data = {"outsideArea": False, "transactionType": "rent", "maxPrice": self.filter.max_price,
                "minSurface": self.filter.min_area,
                "types": ["maison", "appartement"],
                "indoor": ["furnished"] if self.filter.furnished else [],
                "outdoor": [], "otherRooms": [],
                "locations": self.locations}
        res = await self.client.patient_fetch(HTTPRequest(method='POST',
                                                          url='https://www.orpi.com/api/search?sort=blurredness-up%2C_geodistance-up%2Cdate-up',
                                                          body=json.dumps(data), headers=self.headers))
        res_json = res.json()
        for c in res_json['estates']:
            await self.push_candidate(c)

    async def search_locations(self):
        resp, _ = await asyncio.wait([
            self.client.patient_fetch(
                HTTPRequest(url='https://www.orpi.com/api/search/autocomplete/' + str(i),
                            headers=self.headers))
            for i in self.filter.arrondissements
        ])
        return [r.result().json()['zipcode'][0]['value'] for r in resp]


if __name__ == '__main__':
    f = Filter(arrondissements=[75001, 75002, 75018], max_price=13000, min_area=25)
    service = Orpi(f, False)
    asyncio.get_event_loop().run_until_complete(service.run())

