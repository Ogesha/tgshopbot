from typing import List
from app.config import CategoryConf

def pick_category_name(title: str, categories_conf: List[CategoryConf]) -> str | None:
    t = (title or "").lower()
    best = None
    for conf in categories_conf:
        name = conf.name
        kws = [k.lower() for k in conf.keywords]
        if not kws:
            if best is None:
                best = name
            continue
        if any(k in t for k in kws):
            return name
    return best
