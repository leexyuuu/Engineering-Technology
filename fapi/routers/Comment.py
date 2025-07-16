from fastapi import Depends, HTTPException,Header
from sqlalchemy.orm import Session
from sqlalchemy import desc,and_, or_,func
from typing import Optional, List
from schemas import Comment,CommentCreate,CommentUpdate
from base import app,get_db
import time
from models import CommentModel,UserModel,ContentModel,ReplyModel
from login import checkUserAndAdmin,checkEdit
from datetime import datetime, timedelta

@app.get("/comment/{content_id}")
def read_comment(content_id: int, db: Session = Depends(get_db)):
    """
    获取指定ID的内容信息
    """
    db_content = db.query(CommentModel).filter(CommentModel.id == content_id).first()
    if db_content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return {"code":20000,"data":db_content}


@app.get("/comment/list/")
def commentlist(
    page: int = 0, limit: int = 100,
                userId: Optional[int] = None,
                contentId: Optional[int] = None,
                db: Session = Depends(get_db)) :
    c = aliased(CommentModel)
    r = aliased(ReplyModel)
    # 使用子查询获取每个评论的第一条回复
    first_reply_subquery = (
        db.query(ReplyModel)
        .filter(c.id == r.commentId)
        .order_by(desc(r.id))
        .limit(1)
        .subquery()
    )
    # 使用子查询计算每个评论的回复总数
    reply_count_subquery = (
        db.query(func.count(r.id))
        .filter(c.id == r.commentId)
        .subquery()
    )
    query = (
        db.query(c, UserModel.nick_name,UserModel.avatar_url,first_reply_subquery.c, reply_count_subquery)
        .outerjoin(UserModel, CommentModel.userId == UserModel.id)
        .outerjoin(first_reply_subquery, c.id == first_reply_subquery.c.commentId)
        .group_by(c)
    )
    totalCountQuery=db.query(c.id)
    if userId and userId>0:
        query = query.filter(CommentModel.userId == userId)
        totalCountQuery = totalCountQuery.filter(CommentModel.userId == userId)
    if contentId and contentId>0:
        query = query.filter(CommentModel.contentId == contentId)
        totalCountQuery = totalCountQuery.filter(CommentModel.contentId == contentId)
    total=totalCountQuery.count()
    res = query.order_by(desc(CommentModel.top,CommentModel.id)).offset((page-1)*limit).limit(limit).all()
    list=[]
    for row in res:
        item=row[0]
        nick_name=row[1]
        avatar_url=row[2]
        reply=row[3]
        item.nick_name=nick_name
        item.avatar_url=avatar_url
        item.reply=reply
        item.replyCount=row[4]
        list.append(item)
    return {"code":20000,"data":{"total":total,"items":list}}

@app.get("/comment/search/")
def search_comment(
    page: int = 0, limit: int = 100,
    txt: Optional[str] = None,
                userId: Optional[int] = None,
                contentId: Optional[int] = None,
                db: Session = Depends(get_db)) :
    """搜索小区"""
    query = db.query(CommentModel,UserModel.nick_name,UserModel.avatar_url,ContentModel.title).outerjoin(UserModel, CommentModel.userId == UserModel.id).outerjoin(ContentModel, CommentModel.contentId == ContentModel.id)
    
    if txt and len(txt)>0:
        query = query.filter(CommentModel.content.like(f"%{txt}%"))
    if userId and userId>0:
        query = query.filter(CommentModel.userId == userId)
    if contentId and contentId>0:
        query = query.filter(CommentModel.contentId == contentId)
    total=query.count()
    res = query.order_by(desc(CommentModel.id)).offset((page-1)*limit).limit(limit).all()
    list=[]
    for row in res:
        item=row[0]
        nick_name=row[1]
        avatar_url=row[2]
        title=row[3]
        item.nick_name=nick_name
        item.avatar_url=avatar_url
        item.title=title
        list.append(item)
    return {"code":20000,"data":{"total":total,"items":list}}

@app.post("/comment/create")
def create_comment(content: CommentCreate=Depends(), token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    """
    创建新内容
    """
    if content.userId <= 0:
         raise HTTPException(status_code=404, detail="请选择用户")
    checkEdit(token,content.userId)
    commentA=db.query(ContentModel).filter(ContentModel.id == content.contentId).first()
    if commentA is None:
        raise HTTPException(status_code=404, detail="Content not found")
    db_content = CommentModel(**content.dict())

    if commentA.userId==content.userId:
        db_content.isAutor=True
    else:
        db_content.isAutor=False
    
    db_content.timestamp=datetime.now()
    db.add(db_content)
    db.commit()
    db.refresh(db_content)
    return {"code":20000,"data":db_content}

@app.put("/comment/update")
def update_comment(content: CommentUpdate=Depends(),token: str = Header(..., alias="Authorization"), db: Session = Depends(get_db)):
    """
    更新指定ID的内容信息
    """
    checkEdit(token,content.userId)
    db_content = db.query(CommentModel).filter(CommentModel.id == content.id).first()
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

@app.delete("/comment/{content_id}")
def delete_comment(content_id: int, token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    """
    删除指定ID的内容
    """
   
    db_content = db.query(CommentModel).filter(CommentModel.id == content_id).first()
    if db_content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    checkEdit(token,db_content.userId)
    db.delete(db_content)
    db.commit()
    return {"code":20000,"data":db_content}