from fastapi import Depends, HTTPException,Header,Form
from sqlalchemy.orm import Session
from typing import List
from schemas import Area,AreaCreate,AreaUpdate
from base import app,get_db
from sqlalchemy import desc

from models import AreaModel,CityModel
from admin import checkToken


@app.get("/area/{area_id}")
def read_area(area_id: int, db: Session = Depends(get_db)):
    """
    获取指定ID的区域信息
    """
    db_area = db.query(AreaModel).filter(AreaModel.id == area_id).first()
    if db_area is None:
        raise HTTPException(status_code=404, detail="Area not found")

    return {"code":20000,"data":db_area}

@app.get("/area/list/")
def read_areas(page: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    获取区域列表，支持分页
    """

    total = db.query(AreaModel).count()
    res = db.query(AreaModel,CityModel.name.label('city')).outerjoin(CityModel, AreaModel.cityId == CityModel.id).offset((page-1)*limit).limit(limit).all()
    list=[]
    for row in res:
        area=row[0]
        city=row[1]
        area.city=city
        list.append(area)

    return {"code":20000,"data":{"total":total,"items":list}}

@app.get("/area/city/{city_id}")
def read_areas_by_city(city_id: int, token: str = Header(..., alias="Authorization"), db: Session = Depends(get_db)):
    """
    获取指定城市的所有区域
    """
    checkToken(token)
    query=db.query(AreaModel).filter(AreaModel.cityId== city_id)
    total=query.count()
    list= query.all()
    return {"code":20000,"data":{"total":total,"items":list}}

@app.post("/area/create")
def create_area(area: AreaCreate = Depends(), token: str = Header(..., alias="Authorization"), db: Session = Depends(get_db)):
    """
    创建新区域
    """
    if len(area.name) < 2:
         raise HTTPException(status_code=404, detail="名称的长度必须大于等于2")
    checkToken(token)
    db_area = AreaModel(**area.dict())
    db.add(db_area)
    db.commit()
    db.refresh(db_area)
    return {"code":20000,"data":db_area}


@app.put("/area/update")
def update_area(area: Area = Depends(), token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    """
    更新指定ID的区域信息
    """
    if len(area.name) < 2:
         raise HTTPException(status_code=404, detail="名称的长度必须大于等于2")
    checkToken(token)
    db_area = db.query(AreaModel).filter(AreaModel.id == area.id).first()
    if db_area is None:
        raise HTTPException(status_code=404, detail="Area not found")
    
    for key, value in area.dict(exclude_unset=True).items():
        setattr(db_area, key, value)
    
    db.commit()
    db.refresh(db_area)
    return {"code":20000,"data":db_area}

@app.delete("/area/{area_id}", response_model=Area)
def delete_area(area_id: int, db: Session = Depends(get_db)):
    """
    删除指定ID的区域
    """
    db_area = db.query(AreaModel).filter(AreaModel.id == area_id).first()
    if db_area is None:
        raise HTTPException(status_code=404, detail="Area not found")
    
    db.delete(db_area)
    db.commit()
    return db_area 

@app.get("/area/search/")
def search_areas(name: str ='',db: Session = Depends(get_db)):
    """
    获取城市列表，支持分页
    """

    query = db.query(AreaModel)
    
    if name and len(name.strip()) > 0:
        query = query.filter(AreaModel.name.like(f"%{name}%"))
   
    list= query.order_by(desc(AreaModel.id)).all()
    total=len(list)
    return {"code":20000,"data":{"total":total,"items":list}}