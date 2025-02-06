from typing import List, Any
from crud import DatabaseHelper
import models 

def orm_to_dict(obj: Any) -> dict:
    """
    Convert a single SQLAlchemy ORM object to a dictionary.
    Filters out private attributes and internal SQLAlchemy state.
    """
    if not obj:
        return {}

    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}

def orm_list_to_dict(obj_list: List[Any]) -> List[dict]:
    """
    Convert a list of SQLAlchemy ORM objects to a list of dictionaries.
    """
    return [orm_to_dict(obj) for obj in obj_list]

def reformat_date(items, column):
    """
    Reformat the date in the given list of items.
    """
    for item in items:
        value = getattr(item, column, None)
        if value and hasattr(value, 'strftime'):
            setattr(item, column, value.strftime("%Y-%m-%d %H:%M:%S"))
    return items

def run_scrapper(website_id: int, url: str):
    db = DatabaseHelper()
    website = db.get_single(models.Website, website_id)
    from scrapper.scrapper import EmbeddingService
    #scrape the website
    service = EmbeddingService()
    website_id = website_id
    url = url
    success = service.scrape_website(website_id, url)
    db.update(models.Website, website_id, {"status":1})