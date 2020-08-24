import asyncio

import logging

from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService


class StarterService(AbstractService):

    def __init__(self, f: Filter, enable_proxy=None) -> None:
        super().__init__(f, enable_proxy)

    def get_candidate_native_id(self, candidate) -> str:
        # candidate entity id extractor
        return super().get_candidate_native_id(candidate)

    async def candidate_to_notification(self, c) -> Notification:
        # convert raw flat entity to a find_a_flat.notification_sender.Notification
        return await super().candidate_to_notification(c)

    async def run(self):
        # Main entry point
        # White scraper here use self.push_candidate(candidate) passing a raw website flat entity
        return await super().run()


if __name__ == '__main__':
    f = Filter(arrondissements=[75001, 75002, 75003], max_price=1300, min_area=25)
    service = StarterService(f, False)
    asyncio.get_event_loop().run_until_complete(service.run())

