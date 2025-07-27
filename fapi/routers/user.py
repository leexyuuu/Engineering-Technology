from typing import List,Optional
from fastapi import  Depends, HTTPException,Header
from sqlalchemy.orm import Session
from sqlalchemy import desc,and_, or_
from database import SessionLocal, engine, Base
from models import UserModel,AreaModel,CellModel
from schemas import User,UserUpdate
from base import app,get_db
import login
import time
from datetime import datetime, timedelta
from admin import checkToken


@app.get("/user/me",)
async def readMe(token: str = Header(..., alias="Authorization")):
    user = login.checkToken(token)
    if user==None:
        return user
    return {"code":20000,"data":login.safeUser(user)}

@app.get("/user/search/")
def search_users(
    page: int = 0, limit: int = 100,areaId:int=0,
    txt: Optional[str] = None, db: Session = Depends(get_db)) :
    query = db.query(UserModel,AreaModel.name.label('area'),CellModel.name.label('cell')).outerjoin(AreaModel, UserModel.areaId == AreaModel.id).outerjoin(CellModel, UserModel.cellId == CellModel.id)
    if txt and len(txt)>0:
        id=int(txt)
        if id>0:
            query = query.filter(UserModel.id==id)
        else:
            query = query.filter(UserModel.nick_name.like(f"%{txt}%"))
    if areaId and areaId>0:
        query = query.filter(UserModel.areaId==areaId)
    total=query.count()
    res = query.order_by(desc(UserModel.id)).offset((page-1)*limit).limit(limit).all()
    list=[]
    for row in res:
        item=row[0]
        area=row[1]
        cell=row[2]
        item.area=area
        item.cell=cell
        list.append(item)
   
    return {"code":20000,"data":{"total":total,"items":list}}

# 更新用户
@app.put("/users/update")
def updateUser(user: UserUpdate= Depends(),token: str = Header(..., alias="Authorization"), db: Session = Depends(get_db)):
    login.checkEdit(token,user.id)
    db_user = db.query(UserModel).filter(UserModel.id == user.id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    for key, value in user.dict(exclude_unset=True).items():
        setattr(db_user, key, value)
    db_user.updated_at=datetime.now()
    db.commit()
    db.refresh(db_user)
    return {"code":20000,"data":db_user}
