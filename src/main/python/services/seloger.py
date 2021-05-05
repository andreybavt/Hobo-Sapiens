import urllib.parse

from tornado.httpclient import HTTPRequest

from crawler_utils.utils import *
from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService


class Seloger(AbstractService):
    url = "https://api-seloger.svc.groupe-seloger.com/api/v1/listings/search"
    headers = None

    def get_candidate_native_id(self, pub):
        return pub.get('id')

    async def candidate_to_notification(self, c) -> Notification:
        res = await self.client.patient_fetch(HTTPRequest(method='GET',
                                                          headers=self.headers,
                                                          url=f'https://api-seloger.svc.groupe-seloger.com/api/v1/listings/{c["id"]}'))
        res = res.json()
        return Notification(
            price=c.get('price'),
            location=c.get('zipCode'),
            area=c.get('livingArea'),
            url=c.get('permalink'),
            pics_urls=c.get('photos'),
            description=res.get('description'),
            rooms=res.get('rooms')
        )

    def arr_to_searr(self, arr):
        return 750100 + arr - 75000

    def init_auth_token(self):
        import requests
        self.headers = {
            'user-agent': 'okhttp/4.6.0',
            'User-Agent': 'okhttp/4.6.0'
        }
        seloger_token_host = os.environ.get('HS_SELOGER_TOKEN_HOST', 'localhost')
        seloger_token_port = os.environ.get('HS_SELOGER_TOKEN_PORT', '8001')

        SELOGER_SECURITY_URL = "https://api-seloger.svc.groupe-seloger.com/api/security"
        time_token = requests.get(f"{SELOGER_SECURITY_URL}/register", headers=self.headers).json()

        challenge_url = f"http://{seloger_token_host}:{seloger_token_port}/seloger-auth?{urllib.parse.urlencode(time_token, doseq=False)}"
        token = requests.get(challenge_url).text
        final_token = requests.get(f"{SELOGER_SECURITY_URL}/challenge",
                                   headers={**self.headers, **{'authorization': f'Bearer {token}'}}).text[1:-1]

        self.headers = {
            'accept': 'application/json',
            'user-agent': 'Mobile;Android;SeLoger;6.4.2',
            'authorization': f'Bearer {final_token}',
            'content-type': 'application/json; charset=utf-8'
        }
        self.logger.info(f"Initialized token: {final_token}")

    def data(self, page):
        res = {"pageSize": 50,
               "pageIndex": page,
               "query": {"realtyTypes": 3,
                         "minimumLivingArea": self.filter.min_area,
                         "sortBy": 0,
                         "maximumPrice": self.filter.max_price,
                         "transactionType": 1,
                         "inseeCodes": [str(self.arr_to_searr(i)) for i in self.filter.arrondissements]},
               }
        if self.filter.furnished:
            res['query']["furnishing"] = 1
        return res

    async def run(self):
        self.init_auth_token()

        for page in range(1, 10):
            res = await self.client.patient_fetch(
                HTTPRequest(method="POST", url=self.url, body=json.dumps(self.data(page)), headers=self.headers))
            res_json = res.json()
            for c in res_json['items']:
                await self.push_candidate(c)
            if page == res_json['pageCount']:
                break


if __name__ == '__main__':
    pub_filter = Filter(arrondissements=[75001],
                        furnished=True,
                        max_price=1300,
                        min_area=25)
    seloger = Seloger(pub_filter, False)
    asyncio.get_event_loop().run_until_complete(seloger.run())
    print(len(seloger.notifications))