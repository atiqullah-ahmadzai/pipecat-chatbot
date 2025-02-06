from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database import SessionLocal
import models 
from fastapi.responses import JSONResponse
from helpers import *
from fastapi.encoders import jsonable_encoder
from typing import Generator
from crud import DatabaseHelper

db = DatabaseHelper()
        
templates = Jinja2Templates(directory="templates")
router    = APIRouter()
rsp       = {"status":True, "message": "Operation successful", "data": []}
templates = Jinja2Templates(directory="templates")

## GET Routes ##
@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    data = {}
    data['urls'] = db.get_all(models.Website,filters={},order_by='-id')
    return templates.TemplateResponse("index.html", {"request": request, "data": data})

@router.get("/website", response_class=HTMLResponse)
async def get_websites(request: Request):
    data         = {}
    urls = db.get_all(models.Website,filters={},order_by='-id')
    data['urls'] = (urls)
    return JSONResponse(jsonable_encoder(data))

@router.get("/chat/{id}", response_class=HTMLResponse)
async def read_chat(request: Request, id: int):
    data = {}
    data['chats'] = db.get_all(models.Chat,filters={"website_id":id},order_by='id')
    data['id']    = id
    data['website'] = db.get_single(models.Website,id)
    return templates.TemplateResponse("chat.html", {"request": request, "data": data})

@router.get("/voice/{id}", response_class=HTMLResponse)
async def voice_chat(request: Request, id: int):
    data = {}
    data['chats'] = db.get_all(models.Chat,filters={"website_id":id},order_by='id')
    data['id']    = id
    data['website'] = db.get_single(models.Website,id)
    return templates.TemplateResponse("voice.html", {"request": request, "data": data})

@router.get("/website/delete/{id}", response_class=HTMLResponse)
async def delete_website(request: Request, id: int):
    db.delete(models.Website,id)
    db.delete_all(models.Chat,filters={"website_id":id})
    rsp["status"] = True
    rsp["message"] = "Website deleted successfully"
    rsp["data"] = []
    
    return JSONResponse(jsonable_encoder(rsp))



## POST Routes ##
@router.post("/website/create")
async def create_website(request: Request, background_tasks: BackgroundTasks):
    data = await request.form()
    url = data.get("url")
    sublinks = data.get("sublinks")
    existing_url = db.get_all(models.Website,filters={"url":url},order_by='-id')
    if existing_url:
        
        rsp["status"]  = False
        rsp["message"] = "URL already exists!"
        return rsp
    else:
        new_item = db.create(models.Website, {
            'url': url,
            'sublinks': sublinks
        })
        
        background_tasks.add_task(run_scrapper, new_item.id, new_item.url)
    
        rsp["status"]  = True
        rsp["message"] = "Website is being prosessed"
        return rsp

@router.post("/website/update")
async def update_website(request: Request):
    data = await request.form()
    id = int(data.get("id"))
    url = data.get("url")
    sublinks = data.get("sublinks")
    
    db.update(models.Website, id, {
        'url': url,
        'sublinks': sublinks
    })
    
    rsp["status"]  = True
    rsp["message"] = "Website updated successfully"
    
    return JSONResponse(jsonable_encoder(rsp))
@router.post("/chat/ask")
async def ask_ai(request: Request):
    data = await request.form()
    query  = data.get("query")
    website_id = int(data.get("id"))
    
    website = db.get_single(models.Website,website_id)
    chat_item = db.create(models.Chat, {
        'query': query,
        'website_id': website_id,
    })

    
    from scrapper.scrapper import EmbeddingService
    from llm import GroqService
    
    service = EmbeddingService()
    llm = GroqService()
    
    vector_result = service.query(website_id,website.url,query)
    response = llm.ask_ai(vector_result)
    
    chat_item2 = db.create(models.Chat, {
        'response': response,
        'website_id': website_id,
        'query': query,
        'prompt': vector_result[0],
        'sent': 1
    })
    
    return {"status": True, "message": "Operation successful", "data": response}
    
    
    
    
    
    