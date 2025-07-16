from fastapi import Depends, HTTPException,Header
from sqlalchemy.orm import Session
from sqlalchemy import desc,and_, or_
from typing import Optional, List
from schemas import Content,ContentCreate,ContentUpdate
from base import app,get_db
from models import ContentModel,AreaModel,UserModel
from admin import checkToken
from login import checkUserAndAdmin,checkEdit
from datetime import datetime, timedelta

@app.get("/article/{content_id}")
def read_content(content_id: int, db: Session = Depends(get_db)):
    """
    获取指定ID的内容信息
    """
    row= db.query(ContentModel,AreaModel.name.label('area'),UserModel.nick_name.label('author')).outerjoin(AreaModel, ContentModel.areaId == AreaModel.id).outerjoin(UserModel, ContentModel.userId== UserModel.id).filter(ContentModel.id == content_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Content not found")
    item=row[0]
    area=row[1]
    author=row[2]
    item.area=area
    item.author=author
    return {"code":20000,"data":item}

@app.get("/article/list/")
def rarticlelist(page: int = 0, limit: int = 100,type:int=0,db: Session = Depends(get_db)):
    """
    获取内容列表，支持分页
    """
    total=db.query(ContentModel).count()
    query=db.query(ContentModel)
    if type and type>0:
        query = query.filter(ContentModel.type1 == type)
    
    list=query.order_by(desc(ContentModel.id)).offset((page-1)*limit).limit(limit).all()
    return {"code":20000,"data":{"total":total,"items":list}}

@app.get("/article/recommend")
def rarticlerecommend(page: int = 0, limit: int = 100,db: Session = Depends(get_db)):
    """
    获取内容列表，支持分页
    """
    total=db.query(ContentModel).count()
    list=db.query(ContentModel).order_by(desc(ContentModel.id)).offset((page-1)*limit).limit(limit).all()
    return {"code":20000,"data":{"total":total,"items":list}}



@app.get("/article/search/")
def search_content(
    page: int = 0, limit: int = 100,
    txt: Optional[str] = None,
                type: Optional[int] = None,
                userId: Optional[int] = None,
                areaId: Optional[int] = None,
                cellId: Optional[int] = None, db: Session = Depends(get_db)) :
    """搜索小区"""
    query = db.query(ContentModel,AreaModel.name.label('area'),UserModel.nick_name.label('author')).outerjoin(AreaModel, ContentModel.areaId == AreaModel.id).outerjoin(UserModel, ContentModel.userId== UserModel.id)
    
    if txt and len(txt)>0:
        query = query.filter(or_(ContentModel.content.like(f"%{txt}%"),ContentModel.title.like(f"%{txt}%")))
    if type and type>0:
        query = query.filter(ContentModel.type == type)
    if userId and userId>0:
        query = query.filter(ContentModel.userId == userId)
    if areaId and areaId>0:
        query = query.filter(ContentModel.areaId == areaId)
    if cellId and cellId>0:
        query = query.filter(ContentModel.cellId== cellId)
    total=query.count()
    res = query.order_by(desc(ContentModel.id)).offset((page-1)*limit).limit(limit).all()
    list=[]
    for row in res:
        item=row[0]
        area=row[1]
        author=row[2]
        item.area=area
        item.author=author
        list.append(item)
    return {"code":20000,"data":{"total":total,"items":list}}

@app.post("/article/create")
def create_content(content: ContentCreate = Depends(), token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    """
    创建新内容
    """
    checkEdit(token,content.userId)
    user=db.query(UserModel).filter(UserModel.id==content.userId).first()
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    db_content = ContentModel(**content.dict())
    db_content.timestamp=datetime.now()
    db_content.cellId=user.cellId
    db_content.areaId=user.areaId
    db_content.cityId=user.cityId
    db_content.like_count=0
    db_content.collect_count=0
    db.add(db_content)
    db.commit()
    db.refresh(db_content)
    return {"code":20000,"data":db_content}

@app.put("/article/update")
def update_content(content: ContentUpdate= Depends(),token: str = Header(..., alias="Authorization"), db: Session = Depends(get_db)):
    checkEdit(token,content.userId)
    db_content = db.query(ContentModel).filter(ContentModel.id == content.id).first()

    if db_content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    if db_content.userId!=content.userId:
        raise HTTPException(status_code=404, detail="Content not found")
    
    for key, value in content.dict(exclude_unset=True).items():
        setattr(db_content, key, value)

    db_content.updateTime=datetime.now()
    
    db.commit()
    db.refresh(db_content)
    return {"code":20000,"data":db_content}

@app.delete("/article/{content_id}")
def delete_content(content_id: int, token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    """
    删除指定ID的内容
    """
    db_content = db.query(ContentModel).filter(ContentModel.id == content_id).first()
    if db_content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    checkEdit(token,db_content.userId)
    db.delete(db_content)
    db.commit()
    return {"code":20000,"data":db_content}