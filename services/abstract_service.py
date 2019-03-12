import logging
from typing import Optional

from crawler_utils.async_proxy import AsyncProxyClient
from crawler_utils.utils import PersistentSet
from notification_sender import Notification
from runner import Filter


class AbstractService:

    def __init__(self, f: Filter) -> None:
        super().__init__()
        self.filter = f
        self.client = AsyncProxyClient(with_proxy=True)
        self.seen_ids = PersistentSet()
        self.notifications = []

    def get_service_name(self) -> str:
        raise Exception("Not implemented")

    def get_candidate_native_id(self, candidate):
        raise Exception("Not implemented")

    async def candidate_to_notification(self, candidate) -> Notification:
        raise Exception("Not implemented")

    async def run(self):
        raise Exception("Not implemented")

    def get_service_prefixed_id(self, pub):
        return f"{self.get_service_name()}__{self.get_candidate_native_id(pub)}"

    async def push_candidate(self, candidate):
        prefixed_id = self.get_service_prefixed_id(candidate)
        is_seen = await self.seen_ids.has(prefixed_id)
        if is_seen:
            return False
        notification = await self._candidate_to_notification(candidate)
        if notification:
            self.notifications.append(notification)
        return notification

    async def _candidate_to_notification(self, candidate) -> Optional[Notification]:
        notification = await self.candidate_to_notification(candidate)
        if not notification:
            return
        notification.id = self.get_service_prefixed_id(candidate)
        notification.source = self.get_service_name()
        return notification

    async def filter_out_seen(self, candidates):
        return [e for e in candidates if not await self.seen_ids.has(self.get_service_prefixed_id(e))]

    async def main_run(self):
        logging.info(f"Running for {self.get_service_name()}")
        await self.run()
