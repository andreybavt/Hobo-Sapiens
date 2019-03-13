import asyncio
import time

import jsonpickle
import logging
import os


class Filter:
    def __init__(self, arrondissements, max_price, min_area, furnished=None) -> None:
        super().__init__()
        self.arrondissements = arrondissements
        self.max_price = max_price
        self.min_area = min_area
        self.furnished = furnished


if __name__ == '__main__':
    if not os.environ.get('AF_TELEGRAM_BOT_TOKEN'):
        raise Exception('Environment variable AF_TELEGRAM_BOT_TOKEN should be set to telegram bot token')

    if not os.environ.get('AF_TELEGRAM_CHAT_ID'):
        raise Exception('Environment variable AF_TELEGRAM_CHAT_ID should be set to destination chat id')

    from services.bienici import BienIci
    from services.pap import Pap
    from notification_sender import NotificationSender
    from services.seloger import Seloger
    from services.laforet import Laforet
    from services.leboncoin import LeBonCoin

    notification_sender = NotificationSender()

    with open('filter.json', 'r') as  f:
        pub_filter = jsonpickle.decode(f.read())

    service_classes = [BienIci, Seloger, Laforet, LeBonCoin, Pap]
    services = [s(pub_filter) for s in service_classes]
    loop = asyncio.get_event_loop()
    while True:
        last_run = time.time()
        for service in services:
            loop.run_until_complete(service.main_run())
            for (i, n) in enumerate(set(service.notifications)):
                if not len(n.pics_urls):
                    continue
                logging.info(
                    f"Sending notification {i + 1} of {len(service.notifications)} for {service.get_service_name()}")
                notification_sender.send_to_chat(n)
                time.sleep(1)
                loop.run_until_complete(service.seen_ids.add(n.id))
        time.sleep(max(60 * 5 - (time.time() - last_run), 0))
