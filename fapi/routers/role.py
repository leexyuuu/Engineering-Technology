from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from schemas import Role,RoleCreate,RoleUpdate
from base import app,get_db
from models import RoleModel

@app.get("/admin/role/{role_id}", response_model=Role)
def read_role(role_id: int, db: Session = Depends(get_db)):
    """
    获取指定ID的区域信息
    """
    db_role = db.query(RoleModel).filter(RoleModel.id == role_id).first()
    if db_role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return db_role

@app.get("/admin/role/list", response_model=List[Role])
def read_roles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    获取区域列表，支持分页
    """
    return db.query(RoleModel).offset(skip).limit(limit).all()


@app.post("/admin/role", response_model=Role)
def create_role(role: RoleCreate, db: Session = Depends(get_db)):
    """
    创建新区域
    """
    db_role = RoleModel(**role.dict())
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

@app.put("/admin/role/{role_id}", response_model=Role)
def update_role(role_id: int, role: RoleUpdate, db: Session = Depends(get_db)):
    """
    更新指定ID的区域信息
    """
    db_role = db.query(RoleModel).filter(RoleModel.id == role_id).first()
    if db_role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    
    for key, value in role.dict(exclude_unset=True).items():
        setattr(db_role, key, value)
    
    db.commit()
    db.refresh(db_role)
    return db_role

@app.delete("/admin/role/{role_id}", response_model=Role)
def delete_role(role_id: int, db: Session = Depends(get_db)):
    """
    删除指定ID的区域
    """
    db_role = db.query(RoleModel).filter(RoleModel.id == role_id).first()
    if db_role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    
    db.delete(db_role)
    db.commit()
    return db_role 