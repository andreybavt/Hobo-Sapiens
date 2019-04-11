import asyncio
import time

import jsonpickle
import logging
import os
import traceback


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
    from services.figaro import Figaro
    from services.avendre_alouer import AvendreAlouer
    from services.century21 import Century21
    from services.louervite import LouerVite
    from services.meilleursagents import MeilleursAgents
    from services.logicimmo import LogicImmo

    notification_sender = NotificationSender()

    with open('filter.json', 'r') as  f:
        pub_filter = jsonpickle.decode(f.read())

    service_classes = [LogicImmo, MeilleursAgents, LouerVite, Century21, AvendreAlouer, Figaro, BienIci, Seloger,
                       Laforet,
                       LeBonCoin, Pap]
    services = [s(pub_filter) for s in service_classes]
    loop = asyncio.get_event_loop()
    while True:
        last_run = time.time()
        for service in services:
            try:
                loop.run_until_complete(service.main_run())
            except Exception as e:
                logging.error(e, traceback.format_exc())
            for (i, n) in enumerate(set(service.notifications)):
                if not n.pics_urls or not len(n.pics_urls):
                    continue
                logging.info(
                    f"Sending notification {i + 1} of {len(service.notifications)} for {service.get_service_name()}")
                notification_sender.send_to_chat(n)
                loop.run_until_complete(service.seen_ids.add(n.id))
                time.sleep(0.5)
        time.sleep(max(60 * 3 - (time.time() - last_run), 0))
