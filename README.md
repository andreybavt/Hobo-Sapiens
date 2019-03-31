# ApartFacile 
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
AF_TELEGRAM_BOT_TOKEN="XXX" AF_TELEGRAM_CHAT_ID="XXX" python3 runner.py
```

Where the environment variables are:

`AF_TELEGRAM_BOT_TOKEN` - contains telegram bot token

`AF_TELEGRAM_CHAT_ID` - contains telegram chat id where the notifications will be posted

## Currently supported agencies:

- Bienici
- Laforet
- Leboncoin
- PAP
- Seloger
- Figaro Immo
- AvendreAlouer
- Century21
- LouerVite
- MeilleursAgents
- LogicImmo

## Contribution
Contribution is welcome. It's best to add more proxy retrievers or/and agencies websites scrappers.

### New proxy retriever:
  Proxy management is done in `crawler_utils.async_proxy.ProxyManager#fetch_proxies`
  
  In order to add another proxy provider you can add another function like `fetch_a2u` that returns a list of 
  
  `crawler_utils.async_proxy.Proxy`
  
  and call this new function below like:
  
  `all_found_proxies_result += fetch_clarketm()`
  
### New agency scrapper:
  All agency scrappers have the same tructure inheriting 
  
  `services.abstract_service.AbstractService`
  
  In order to add a new one it's best just to copy (and rename) a 
  
  `services.starter_service.StarterService`

  and then write an implementations to methods inside of it
  
  To plug it in add it to the array `service_classes = [...]` in `runner.py`
  
  
