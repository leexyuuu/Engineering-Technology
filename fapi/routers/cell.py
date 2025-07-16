from fastapi import Depends, HTTPException,Header
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from base import app,get_db
from schemas import Cell,CellCreate,CellUpdate
from models import CellModel,CityModel,AreaModel
from admin import checkToken

@app.post("/cell/create")
def create_cell(cell:CellCreate= Depends(), token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    checkToken(token)
    """创建新的小区记录"""
    db_cell = CellModel(**cell.dict())
    db.add(db_cell)
    db.commit()
    db.refresh(db_cell)
    return {"code":20000,"data":db_cell}
  

@app.get("/cell/{cell_id}")
def get_cell(cell_id: int,db: Session = Depends(get_db)):
    """根据ID获取小区信息"""
    db_cell= db.query(CellModel).filter(CellModel.id == cell_id).first()
    return {"code":20000,"data":db_cell}

@app.get("/cell/list/")
def get_cells(page: int = 0, limit: int = 10,db: Session = Depends(get_db)):
    """分页获取小区列表"""
    total=db.query(CellModel).count()
    res = db.query(CellModel,AreaModel.name.label('area')).outerjoin(AreaModel, CellModel.areaId == AreaModel.id).offset((page-1)*limit).limit(limit).all()
    list=[]
    for row in res:
        cell=row[0]
        area=row[1]
        cell.area=area
        list.append(cell)
    return {"code":20000,"data":{"total":total,"items":list}}

@app.put("/cell/update")
def update_cell(cell:Cell= Depends(), token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    checkToken(token)
    """更新小区信息"""
    db_cell = db.query(CellModel).filter(CellModel.id == cell.id).first()
    if not db_cell:
        return None
    for key, value in cell.dict(exclude_unset=True).items():
        setattr(db_cell, key, value)
    db.commit()
    db.refresh(db_cell)
    return {"code":20000,"data":db_cell}


@app.get("/cell/search/")
def search_cells(
                name: Optional[str] = None,
                cityId: Optional[int] = None,
                areaId: Optional[int] = None, db: Session = Depends(get_db)) :
    """搜索小区"""
    query = db.query(CellModel,AreaModel.name.label('area')).outerjoin(AreaModel, CellModel.areaId == AreaModel.id)
    
    if name:
        query = query.filter(CellModel.name.like(f"%{name}%"))
    if cityId:
        query = query.filter(CellModel.cityId == cityId)
    if areaId:
        query = query.filter(CellModel.areaId == areaId)
    res = query.order_by(desc(CellModel.id)).all()
    list=[]
    for row in res:
        cell=row[0]
        area=row[1]
        cell.area=area
       
        list.append(cell)
    return {"code":20000,"data":{"total":len(list),"items":list}}


@app.get("/cell/count/")
def get_cells_count(token: str,
                   name: Optional[str] = None,
                   cityId: Optional[int] = None,
                   areaId: Optional[int] = None, db: Session = Depends(get_db)):
    """获取小区总数（用于分页）"""
    query = db.query(CellModel)
    
    if name:
        query = query.filter(CellModel.name.like(f"%{name}%"))
    if cityId:
        query = query.filter(CellModel.cityId == cityId)
    if areaId:
        query = query.filter(CellModel.areaId == areaId)

    return {"code":20000,"data":query.count()}