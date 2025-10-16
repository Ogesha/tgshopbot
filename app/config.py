import os, yaml
from dataclasses import dataclass
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

@dataclass
class SelectorSet:
    card: List[str]
    title: List[str]
    price: List[str]
    link_from_title: bool = True

@dataclass
class ScrapeConfig:
    urls: list[str]
    daily_time: str
    selectors: SelectorSet

@dataclass
class CategoryConf:
    name: str
    keywords: List[str]

@dataclass
class BroadcastConf:
    autosend_daily_time: str | None
    message_template: str

@dataclass
class AppConfig:
    scrape: ScrapeConfig
    categories: List[CategoryConf]
    broadcast: BroadcastConf
    bot_token: str
    admin_ids: list[int]
    database_url: str
    tz: str

def _read_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_config(yaml_path: str = "config.yaml") -> AppConfig:
    y = _read_yaml(yaml_path)
    bot_token = os.getenv("BOT_TOKEN", "")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN не задан в .env")

    return AppConfig(
        scrape=ScrapeConfig(
            urls=y["scrape"]["urls"],
            daily_time=y["scrape"]["daily_time"],
            selectors=SelectorSet(**y["scrape"]["selectors"])
        ),
        categories=[CategoryConf(**c) for c in y.get("categories", [])],
        broadcast=BroadcastConf(
            autosend_daily_time=y.get("broadcast", {}).get("autosend_daily_time"),
            message_template=y.get("broadcast", {}).get("message_template", "Новости: {count}")
        ),
        bot_token=bot_token,
        admin_ids=[int(x.strip()) for x in os.getenv("ADMIN_IDS","").split(",") if x.strip().isdigit()],
        database_url=os.getenv("DATABASE_URL", "postgresql+asyncpg://shopbot:shopbot@localhost:5432/shopbot"),
        tz=os.getenv("TZ", "UTC"),
    )
