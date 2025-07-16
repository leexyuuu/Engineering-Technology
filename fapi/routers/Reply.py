from fastapi import Depends, HTTPException,Header
from sqlalchemy.orm import Session
from sqlalchemy import desc,and_, or_
from typing import Optional, List
from schemas import Reply,ReplyCreate,ReplyUpdate
from base import app,get_db
from datetime import datetime, timedelta
from models import UserModel,ReplyModel,ContentModel
from login import checkUserAndAdmin,checkEdit,checkToken

@app.get("/reply/{content_id}")
def read_reply(content_id: int, db: Session = Depends(get_db)):
    """
    获取指定ID的内容信息
    """
    db_content = db.query(ReplyModel).filter(ReplyModel.id == content_id).first()
    if db_content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return {"code":20000,"data":db_content}



@app.get("/reply/search/")
def search_reply(
    page: int = 0, limit: int = 100,
    txt: Optional[str] = None,
                userId: Optional[int] = None,
                commentId: Optional[int] = None,
                db: Session = Depends(get_db)) :
    """搜索小区"""
    query = db.query(ReplyModel,UserModel.nick_name,UserModel.avatar_url).outerjoin(UserModel, ReplyModel.userId == UserModel.id)
    
    if txt and len(txt)>0:
        query = query.filter(ReplyModel.content.like(f"%{txt}%"))
    if userId and userId>0:
        query = query.filter(ReplyModel.userId == userId)
    if commentId and commentId>0:
        query = query.filter(ReplyModel.commentId == commentId)
    total=query.count()
    res = query.order_by(desc(ReplyModel.id)).offset((page-1)*limit).limit(limit).all()
    list=[]
    for row in res:
        item=row[0]
        nick_name=row[1]
        avatar_url=row[2]
        item.nick_name=nick_name
        item.avatar_url=avatar_url
        list.append(item)
    return {"code":20000,"data":{"total":total,"items":list}}

@app.post("/reply/create")
def create_reply(content: ReplyCreate=Depends(), token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    """
    创建新内容
    """
    if content.userId <= 0:
         raise HTTPException(status_code=404, detail="请选择用户")
    checkEdit(token,content.userId)
    db_content = ReplyModel(**content.dict())
    commentA=db.query(ContentModel).filter(ContentModel.id == content.contentId).first()
    if commentA.userId==content.userId:
        db_content.isAutor=True
    else:
        db_content.isAutor=False
    db_content.timestamp=datetime.now()
    db.add(db_content)
    db.commit()
    db.refresh(db_content)
    return {"code":20000,"data":db_content}

@app.put("/reply/update")
def update_reply(content: ReplyUpdate=Depends(),token: str = Header(..., alias="Authorization"), db: Session = Depends(get_db)):
    """
    更新指定ID的内容信息
    """
    checkEdit(token,content.userId)
    db_content = db.query(ReplyModel).filter(ReplyModel.id == content.id).first()
    if db_content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    if content.userId!=db_content.userId:
        raise HTTPException(status_code=404, detail="Content not found")
    
    for key, value in content.dict(exclude_unset=True).items():
        setattr(db_content, key, value)
    
    db.commit()
    db.refresh(db_content)
    return {"code":20000,"data":db_content}

@app.delete("/reply/{content_id}")
def delete_reply(content_id: int, token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    """
    删除指定ID的内容
    """
    db_content = db.query(ReplyModel).filter(ReplyModel.id == content_id).first()
    if db_content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    checkEdit(token,db_content.userId)
    db.delete(db_content)
    db.commit()
    return {"code":20000,"data":db_content}