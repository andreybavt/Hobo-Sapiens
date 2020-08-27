import asyncio
import json
from collections import deque
from uuid import uuid4

from tornado.httpclient import HTTPRequest

from runner import Filter
from services.abstract_service import AbstractService

MOSCOW = ((37.362531, 55.920481), (37.856235, 55.561908))

OUT_FILE = open('/tmp/cian', 'w')


class Cian(AbstractService):
    Q = deque()
    auth_url = "https://api.cian.ru/1.4/ios/get-session-anonymous"
    search_url = "https://api.cian.ru/search-offers/v4/search-offers-mobile-apps/"

    headers = None
    requests_since_init = 0
    saved_lines = 0

    def get_candidate_native_id(self, candidate) -> str:
        # candidate entity id extractor
        if 'offer' in candidate:
            return candidate['offer']['id']
        else:
            return candidate['newBuilding']['id']

    async def candidate_to_notification(self, c):
        OUT_FILE.write(json.dumps(c, ensure_ascii=False) + "\n")
        self.saved_lines += 1

    async def run(self):
        await self.init_session()
        self.Q.append(MOSCOW)
        await self.process_queue()

    async def init_session(self):
        _uuid = str(uuid4())
        version_code = 21521300
        self.headers = {
            'os': 'android',
            'buildnumber': '2.152.1',
            'versioncode': str(version_code),
            'device': 'Phone',
            'applicationid': str(_uuid),
            'package': 'ru.cian.main',
            'user-agent': f'Cian/2.152.1 (Android; {version_code}; Phone; Android SDK built for x86; 25; {_uuid})',
            'content-type': 'application/json; charset=UTF-8'
        }
        res = await self.client.fetch(HTTPRequest(method='POST', url=self.auth_url, headers=self.headers, body=""))
        sid = res.json()['data']['sid']
        self.headers['authorization'] = f'simple {sid}'
        self.requests_since_init = 0

    def get_data_for_rect(self, rect):
        tl, br = rect
        return {
            "query": {
                "_type": "flatsale",
                "with_neighbors": {
                    "type": "term",
                    "value": False
                },
                "region": {
                    "type": "terms",
                    "value": [
                        -1
                    ]
                },
                "bbox": {
                    "type": "term",
                    "value": [tl, br]
                },
                "room": {
                    "type": "terms",
                    "value": [
                        1,
                        2,
                        3,
                        4,
                        5,
                        6,
                        9,
                        7
                    ]
                },
                "object_type": {
                    "type": "terms",
                    "value": [
                        0
                    ]
                },
                "building_status": {
                    "type": "term",
                    "value": 0
                },
                "engine_version": {
                    "type": "term",
                    "value": "2"
                },
                "page": {
                    "type": "term",
                    "value": 1
                },
                "limit": {
                    "type": "term",
                    "value": 20
                }
            }
        }

    async def process_queue(self):
        while len(self.Q):
            items_to_process = []
            for i in range(1):
                if len(self.Q):
                    v = self.Q.pop()
                    items_to_process.append(v)
                else:
                    break
            await asyncio.wait([self.process_quadrant(i) for i in items_to_process])

    async def process_quadrant(self, quadrant):
        self.requests_since_init += 1
        if self.requests_since_init >= 5:
            await self.init_session()
        res = await self.client.fetch(
            HTTPRequest(method='POST', url=self.search_url, headers=self.headers,
                        body=json.dumps(self.get_data_for_rect(quadrant))))
        res_json = res.json()
        if res_json['totalCount'] <= 20:
            for c in res_json['items']:
                await self.push_candidate(c)
        else:
            for q in split_4(quadrant):
                self.Q.append(q)


def to_plottable(q):
    (tl_x, tl_y), (br_x, br_y) = q
    return f"{tl_y},{tl_x},\n{br_y},{br_x},"


def mid(one, two):
    return (one + two) / 2


def split_4(quadrant):
    (tl_x, tl_y), (br_x, br_y) = quadrant
    mid_x = mid(tl_x, br_x)
    mid_y = mid(tl_y, br_y)
    return [((tl_x, tl_y), (mid_x, mid_y)),
            ((mid_x, tl_y), (br_x, mid_y)),
            ((tl_x, mid_y), (mid_x, br_y)),
            ((mid_x, mid_y), (br_x, br_y))]


if __name__ == '__main__':
    f = Filter(arrondissements=[75001, 75002, 75003], max_price=1300, min_area=25)
    service = Cian(f, False)
    # pprint(json.dumps(service.get_data_for_rect(MOSCOW)))
    asyncio.get_event_loop().run_until_complete(service.run())
