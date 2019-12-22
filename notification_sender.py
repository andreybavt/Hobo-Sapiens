import json
import logging
import traceback
from os import environ
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

    def __init__(self) -> None:
        super().__init__()
        self.image_manager = ImageManager()
        self.updater = Updater(token=environ.get('AF_TELEGRAM_BOT_TOKEN'),
                               request_kwargs={"connect_timeout": 60., "read_timeout": 60.})

    def send_to_chat(self, notif: Notification):
        desc = f'ID: {notif.id}\nPrice: {notif.price}\nArea: {notif.area}\nWhere: {notif.location}\nURL: {notif.url} '
        try:
            # chat_id = '-1001121437337'
            # chat_id = '73115329'
            chat_id = environ.get('AF_TELEGRAM_CHAT_ID')
            reference_message = None
            if not notif.pics_urls:
                return
            try:
                for c in chunks(notif.pics_urls, 10):
                    new_images, seen_in_messages = self.image_manager.check_all(notif, c)
                    seen_in = None if not len(seen_in_messages) else seen_in_messages.pop()
                    reference_message = None if not seen_in else seen_in['message_id']
                    if reference_message:
                        logging.info(f"Found photo duplicates: \n               {notif.url} vs. {seen_in['notif'].url}")
                    if len(new_images):
                        logging.info(f"Sending {len(new_images)} images")
                        send_pic_res = self._send_pics(new_images.keys(), chat_id, desc,
                                                       reply_to_message_id=reference_message)
                        if hasattr(send_pic_res[0], 'message_id'):
                            self.image_manager.set_message_ids([v['hash'] for v in new_images.values()],
                                                               send_pic_res[0].message_id)
            except Exception as e:
                logging.error(e)

            if len(new_images):
                self._send_message(chat_id, desc, reference_message=reference_message)
        except Exception as e:
            logging.error(e, traceback.format_exc())

    @nofail(retries=20)
    def _send_message(self, chat_id, desc, reference_message=None):
        logging.info(f"Sending message: {chat_id} {desc} {reference_message} ")

        self.updater.bot.send_message(chat_id, desc, timeout=20 * 60, disable_web_page_preview=True,
                                      reply_to_message_id=reference_message,
                                      disable_notification=reference_message is not None)

    @nofail(retries=20)
    def _send_pics(self, c, chat_id, desc, **kwargs):
        return self.updater.bot.send_media_group(chat_id, [InputMediaPhoto(i, caption=desc) for i in c],
                                                 timeout=20 * 60, disable_notification=True, **kwargs)


if __name__ == '__main__':
    NotificationSender().send_to_chat(
        Notification(id="SL", price=1200, location="75003", area=30,
                     url="http://ya.ru",
                     pics_urls=["https://www.python-course.eu/images/venitian_masks.png",
                                "https://cache.lovethispic.com/uploaded_images/thumbs/220227-Keep-Calm-And-Pass-Your-Exams.jpg",
                                "https://poster.keepcalmandposters.com/default/5997547_no_dp_because_exam_chaling.png"])
    )
