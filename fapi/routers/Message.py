from fastapi import Depends, HTTPException,Header
from sqlalchemy.orm import Session
from sqlalchemy import desc,and_, or_,func
from typing import Optional, List
from schemas import Message,MessageBox,MessageCreate,MessageLetter
from base import app,get_db
import time
from models import MessageModel,MessageBoxModel
from login import checkToken


@app.get("/message/grouplist/")
def messageGrouplist(page: int = 0, limit: int = 100,token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    """
    获取内容列表，支持分页
    """
    user = checkToken(token)
    query=db.query(MessageBoxModel).filter(MessageBoxModel.userId == user.id)
    total=query.count()
    list=query.order_by(desc(MessageBoxModel.timestamp)).offset((page-1)*limit).limit(limit).all()
    return {"code":20000,"data":{"total":total,"items":list}}


@app.get("/message/list/")
def messagelist(page: int = 0, limit: int = 100,value:int=0,type:int=0,token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    """
    获取内容列表，支持分页
    """
    user = checkToken(token)
    query=db.query(MessageModel).filter(and_(MessageModel.userId == user.id,MessageModel.value==value,MessageModel.type==type))
    total=query.count()
    list=query.order_by(desc(MessageModel.timestamp)).offset((page-1)*limit).limit(limit).all()
    return {"code":20000,"data":{"total":total,"items":list}}

@app.get("/message/unreadycount/")
def unreadycount(token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    user = checkToken(token)
    total = db.query(func.sum(MessageBoxModel.count)).filter(MessageBoxModel.userId == user.id).scalar()
    return {"code":20000,"data":total}

@app.post("/message/ready/")
def ready(value:int=0,type:int=0,token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    user = checkToken(token)
    item=db.query(MessageBoxModel).filter(and_(MessageBoxModel.userId == user.id,MessageBoxModel.value==value,MessageBoxModel.type==type)).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Content not found")
    item.count=0
    db.query(MessageModel).filter(and_(MessageModel.userId == user.id,MessageModel.value==value,MessageModel.type==type)).update({ready: True}, synchronize_session=False)
    db.commit()
    db.refresh(item)
    return {"code":20000,"data":item}
    

def addMessageBoxOrUpdate(message: MessageCreate ,timestamp:int,db: Session = Depends(get_db)):
    item = db.query(MessageBoxModel).filter(and_(MessageBoxModel.userId == message.userId,MessageBoxModel.value==message.value,MessageBoxModel.type==message.type)).first()
    if item is None:
       db_content = MessageBoxModel(**Message.dict())
       db_content.count=0
       if message.ready!=True:
            db_content.count=1
            
       db_content.timestamp=timestamp
       db.add(db_content)
       db.commit()
       db.refresh(db_content)
    else:
        if message.ready==True:
            item.count=item.count+1
            db.commit()
            db.refresh(item)
      


def createMessage(content: MessageCreate, db: Session = Depends(get_db)):
    db_content = MessageModel(**content.dict())
    db_content.timestamp=time.time()
    if db_content.ready!=True:
        db_content.ready=False
    db.add(db_content)
    db.commit()
    db.refresh(db_content)
    if db_content.id > 0:
       addMessageBoxOrUpdate(content,db_content.timestamp)
    
    return {"code":20000,"data":db_content}

@app.post("/message/seedletter")
def seedLetter(item:MessageLetter,token: str = Header(..., alias="Authorization")):
    user=checkToken(token)
    external_data1 = { 'content':item.content,'images': item.images,'userId':item.userId,'introduction':'管理者','type':1,'value':user.id,'fromUserId':user.id}
    createMessage(MessageCreate(**external_data1))
    external_data2 = { 'content':item.content,'images': item.images,'userId':user.id,'introduction':'管理者','type':1,'value':item.userId,'fromUserId':user.id,'ready':True}
    createMessage(MessageCreate(**external_data2))
    return {"code":20000,"data":True}

@app.delete("/message/deleteletter")
def delete_message(id:int, token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    """
    删除指定ID的内容
    """
    user=checkToken(token)
    item=db.query(MessageModel).filter(MessageModel.id == id).first()
    db.query(MessageModel).filter(MessageModel.id == id).delete()
    db.commit()
    return {"code":20000,"data":True}

@app.put("/message/update")
def update_message(content: Message,token: str = Header(..., alias="Authorization"), db: Session = Depends(get_db)):
    """
    更新指定ID的内容信息
    """
    user=checkToken(token)
    db_content = db.query(MessageModel).filter(MessageModel.id == content.id).first()
    if db_content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    if db_content.userId!=user.id:
        raise HTTPException(status_code=404, detail="Content not found")
    
    for key, value in content.dict(exclude_unset=True).items():
        setattr(db_content, key, value)
    
    db.commit()
    db.refresh(db_content)
    return {"code":20000,"data":db_content}


def deleteMessageUpdateMessageBox(value:int,type:int,userId:int,ready:bool,db: Session = Depends(get_db)):
    count= db.query(MessageModel.id).filter(and_(MessageModel.userId == userId,MessageModel.value==value,MessageModel.type==type)).count()
    if(count<=0):
        db.query(MessageBoxModel).filter(MessageBoxModel.userId == userId,MessageBoxModel.value==value,MessageBoxModel.type==type).delete()
        db.commit()
        return
    if ready:
        item = db.query(MessageBoxModel).filter(MessageBoxModel.userId == userId,MessageBoxModel.value==value,MessageBoxModel.type==type).first()
        if item is None:
            return
        item.count=item.count-1
        if item.count<0:
            item.count=0
        db.commit()
        db.refresh(item)

@app.delete("/message/{content_id}")
def delete_message(content_id: int, token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    """
    删除指定ID的内容
    """
    user=checkToken(token)
    db_content = db.query(MessageModel).filter(Message.id == content_id).first()
    if db_content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    if db_content.userId!=user.id:
      raise HTTPException(status_code=404, detail="Content not found")
    db.delete(db_content)
    db.commit()
    deleteMessageUpdateMessageBox(db_content.value,db_content.type,db_content.userId,db_content.ready)
    return {"code":20000,"data":True}

@app.delete("/message/deletegroup")
def delete_message(value:int,type:int, token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    """
    删除指定ID的内容
    """
    user=checkToken(token)
    db.query(MessageBoxModel).filter(MessageBoxModel.userId == user.id,MessageBoxModel.value==value,MessageBoxModel.type==type).delete()
    db.query(MessageModel).filter(MessageModel.userId == user.id,MessageModel.value==value,MessageModel.type==type).delete()
    db.commit()
    return {"code":20000,"data":True}