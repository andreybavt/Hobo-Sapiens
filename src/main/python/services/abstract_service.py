import logging
import os
import sys
from pathlib import Path

import diskcache as dc
from prometheus_client import Counter, Histogram

logging.basicConfig(stream=sys.stdout, level=os.environ.get('LOGLEVEL', 'INFO').upper(),
                    format='%(asctime)s %(levelname)s %(name)s: %(message)s')

from typing import Optional, Set

from crawler_utils.async_proxy import AsyncProxyClient
from notification_sender import Notification
from runner import Filter


class AbstractService:
    METRICS_RUN_COUNT = Counter('service_runs', 'Number of service runs', ['service'])
    METRICS_INIT_TIME = Histogram('service_init_time_sec', 'Time to initialize a service', ['service'])
    METRICS_RUN_TIME = Histogram('service_run_time_sec', 'Time to run a service', ['service'])
    METRICS_NOTIFICATIONS_COUNT = Counter('service_listing_count', 'Number of notifications found', ['service'])

    def __init__(self, f: Filter, enable_proxy=None,
                 storage_path=Path.home().joinpath('.hobo-sapiens', 'listings')) -> None:

        self.METRICS_RUN_COUNT = self.METRICS_RUN_COUNT.labels(self.get_service_name())
        self.METRICS_INIT_TIME = self.METRICS_INIT_TIME.labels(self.get_service_name())
        self.METRICS_RUN_TIME = self.METRICS_RUN_TIME.labels(self.get_service_name())
        self.METRICS_NOTIFICATIONS_COUNT = self.METRICS_NOTIFICATIONS_COUNT.labels(self.get_service_name())

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("INITIALIZING")
        self.filter = f
        self.client = AsyncProxyClient(enable_proxy=True if enable_proxy is None else enable_proxy, monitoring=True)
        self.client.fetch_opts = {
            "connect_timeout": 8,
            "request_timeout": 40
        }
        self.seen_ids = dc.Cache(str(storage_path))
        self.notifications: Set[Notification] = set()
        if hasattr(self.client, 'proxy_manager'):
            self.client.proxy_manager.penalty_fn = lambda e: 2

    def get_service_name(self) -> str:
        return self.__class__.__name__

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
        if prefixed_id in self.seen_ids:
            return False
        notification = await self._candidate_to_notification(candidate)
        if notification:
            self.notifications.add(notification)
        return notification

    async def _candidate_to_notification(self, candidate) -> Optional[Notification]:
        self.logger.debug(f"Running candidate_to_notification, current nb of notifications: {len(self.notifications)}")
        notification = await self.candidate_to_notification(candidate)
        if not notification or not notification.pics_urls or not len(notification.pics_urls):
            return
        notification.id = self.get_service_prefixed_id(candidate)
        notification.source = self.get_service_name()
        return notification

    async def filter_out_seen(self, candidates):
        return [e for e in candidates if self.get_service_prefixed_id(e) not in self.seen_ids]

    async def main_run(self):
        self.METRICS_RUN_COUNT.inc()

        self.logger.info(f"Running")
        self.notifications = set()
        with self.METRICS_RUN_TIME.time():
            await self.run()

        self.METRICS_NOTIFICATIONS_COUNT.inc(len(self.notifications))
        self.logger.info(f"Ended, number of notifications: {len(self.notifications)}")
