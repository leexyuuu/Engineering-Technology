from fastapi import Depends, HTTPException,Header,Form
from sqlalchemy.orm import Session
from typing import List
from schemas import City,CityCreate,CityUpdate
from base import app,get_db
from models import CityModel
from admin import checkToken
from sqlalchemy import desc


@app.get("/city/{city_id}")
def read_city(city_id: int, db: Session = Depends(get_db)):
    """
    获取指定ID的城市信息
    """
    db_city = db.query(CityModel).filter(CityModel.id == city_id).first()
    if db_city is None:
        raise HTTPException(status_code=404, detail="City not found")
    return {"code":20000,"data":db_city}

@app.get("/city/list/")
def read_cities(page: int = 0, limit: int = 100, token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    """
    获取城市列表，支持分页
    """
    checkToken(token)
    total=db.query(CityModel).count()
    list= db.query(CityModel).offset((page-1)*limit).limit(limit).all()
    return {"code":20000,"data":{"total":total,"items":list}}

@app.get("/city/search/")
def search_cities(name: str ='',db: Session = Depends(get_db)):
    """
    获取城市列表，支持分页
    """

    query = db.query(CityModel)
    
    if name and len(name.strip()) > 0:
        query = query.filter(CityModel.name.like(f"%{name}%"))
   
    list= query.order_by(desc(CityModel.id)).all()
    total=len(list)
    return {"code":20000,"data":{"total":total,"items":list}}



@app.post("/city/create")
def create_city(city: CityCreate = Depends(), token: str = Header(..., alias="Authorization"), db: Session = Depends(get_db)):
    """
    创建新城市
    """
    if len(city.name) < 2:
         raise HTTPException(status_code=404, detail="名称的长度必须大于等于2")
    checkToken(token)
    db_city = CityModel(**city.dict())
    db.add(db_city)
    db.commit()
    db.refresh(db_city)
    return {"code":20000,"data":db_city}


@app.put("/city/update")
def update_city(city: City = Depends(),token: str = Header(..., alias="Authorization"), db: Session = Depends(get_db)):
    """
    更新指定ID的城市信息
    """
    if len(city.name) < 2:
         raise HTTPException(status_code=404, detail="名称的长度必须大于等于2")
    checkToken(token)
    db_city = db.query(CityModel).filter(CityModel.id == city.id).first()
    if db_city is None:
        raise HTTPException(status_code=404, detail="City not found")
    
    for key, value in city.dict(exclude_unset=True).items():
        setattr(db_city, key, value)
    
    db.commit()
    db.refresh(db_city)
    return {"code":20000,"data":db_city}

@app.delete("/city/{city_id}", response_model=City)
def delete_city(city_id: int, db: Session = Depends(get_db)):
    """
    删除指定ID的城市
    """
    db_city = db.query(CityModel).filter(CityModel.id == city_id).first()
    if db_city is None:
        raise HTTPException(status_code=404, detail="City not found")
    
    db.delete(db_city)
    db.commit()
    return db_city 