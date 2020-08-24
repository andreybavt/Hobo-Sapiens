# Hobo Sapiens 
## This is a bot that monitors Parisian real estate agencies and send notifications about new flats to Telegram

## Prerequisites
- Python 3 (optionally a separate virtual environment)
- [Telegram bot](https://core.telegram.org/bots#3-how-do-i-create-a-bot)

## Installation
Clone this repository with `--recursive` flag, then
```
pip install -r requirements.txt
```

## Run
Edit `filter.json` according to your criterias, then:
```
HS_TELEGRAM_BOT_TOKEN="XXX" HS_TELEGRAM_CHAT_ID="XXX" python3 runner.py
```

Where the environment variables are:

`HS_TELEGRAM_BOT_TOKEN` - contains telegram bot token

`HS_TELEGRAM_CHAT_ID` - contains telegram chat id where the notifications will be posted

## Currently supported agencies:

- AvendreAlouer
- BienIci
- Century21
- Figaro
- Laforet
- LeBonCoin
- LogicImmo
- Orpi
- Pap
- Seloger

## Contribution
Contribution is welcome. It's best to add more proxy retrievers or/and agencies websites scrappers.

### New agency scrapper:
  All agency scrappers have the same tructure inheriting 
  
  `services.abstract_service.AbstractService`
  
  In order to add a new one it's best just to copy (and rename) a 
  
  `services.starter_service.StarterService`

  and then write an implementations to methods inside of it
  
  To plug it in add it to the array `service_classes = [...]` in `runner.py`
  
  
