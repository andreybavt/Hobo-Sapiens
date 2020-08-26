import logging
import traceback
from os import environ

from prometheus_client.metrics import Counter, Histogram
from telegram import InputMediaPhoto
from telegram.ext import Updater

from crawler_utils.utils import chunks, nofail
from image_manager import ImageManager


class Notification(object):

    def __init__(self, price=None, location=None, area=None, url=None, pics_urls=None, id=None, source=None, ) -> None:
        super().__init__()
        self.id = id
        self.source = source
        self.price = price
        self.location = location
        self.area = area
        self.url = url
        self.pics_urls = pics_urls

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, o: object) -> bool:
        return isinstance(o, Notification) and o.id == self.id


class NotificationSender:
    logger = logging.getLogger(__name__)
    METRICS_NOTIFICATION_TIME = Histogram("notification_send_time_sec", "Time to send notification", ['type'])
    METRICS_NOTIFICATION_COUNT = Counter("notification_counter", "Number of sent notifications", ['service'])

    def __init__(self) -> None:
        self.image_manager = ImageManager()
        self.updater = Updater(token=environ.get('HS_TELEGRAM_BOT_TOKEN'),
                               request_kwargs={"connect_timeout": 60., "read_timeout": 60.}, use_context=True)

    def send_to_chat(self, notif: Notification):
        desc = f'ID: {notif.id}\nPrice: {notif.price}\nArea: {notif.area}\nWhere: {notif.location}\nURL: {notif.url} '
        self.METRICS_NOTIFICATION_COUNT.labels(notif.source).inc()
        try:
            chat_id = environ.get('HS_TELEGRAM_CHAT_ID')
            reference_message = None
            if not notif.pics_urls:
                return
            new_images = []
            try:
                for c in chunks(notif.pics_urls, 10):
                    new_images, seen_in_messages = self.image_manager.check_all(notif, c)
                    seen_in = None if not len(seen_in_messages) else seen_in_messages.pop()
                    reference_message = None if not seen_in else seen_in.get('message_id')
                    if reference_message:
                        self.logger.info(f"Found photo duplicates: {notif.url} vs. {seen_in['notif'].url}")
                    if len(new_images):
                        self.logger.info(f"Sending {len(new_images)} images")
                        send_pic_res = self._send_pics(new_images.keys(), chat_id, desc,
                                                       reply_to_message_id=reference_message)
                        first_pic = send_pic_res[0]
                        if hasattr(first_pic, 'message_id'):
                            self.image_manager.set_message_ids([v['hash'] for v in new_images.values()],
                                                               first_pic.message_id)
            except Exception as e:
                self.logger.error(e)

            if len(new_images):
                self._send_message(chat_id, desc, reference_message=reference_message)
            else:
                self.logger.info("No new images found, not sending the message")  # TODO: check if price has changed
        except Exception as e:
            self.logger.error(e, traceback.format_exc())

    @nofail(retries=20)
    def _send_message(self, chat_id, desc, reference_message=None):
        with self.METRICS_NOTIFICATION_TIME.labels('message').time():
            log_msg = desc.replace('\n', '; ')
            self.logger.info(f"Sending message: {chat_id} {log_msg} {reference_message} ")

            self.updater.bot.send_message(chat_id, desc, timeout=20 * 60, disable_web_page_preview=True,
                                          reply_to_message_id=reference_message,
                                          disable_notification=reference_message is not None)

    @nofail(retries=20, sleep=0.5, failback_result=None)
    def _send_pics(self, c, chat_id, desc, **kwargs):
        with self.METRICS_NOTIFICATION_TIME.labels('pics').time():
            return self.updater.bot.send_media_group(chat_id, [InputMediaPhoto(i, caption=desc) for i in c],
                                                     timeout=20 * 60, disable_notification=True, **kwargs)
