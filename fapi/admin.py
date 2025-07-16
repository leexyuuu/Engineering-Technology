
from datetime import datetime, timedelta
from typing import Optional
from database import Base
from base import app,get_db
from sqlalchemy.orm import Session
from fastapi import FastAPI, Depends, HTTPException,Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import Column, Text, Integer,String,Date,DateTime,VARCHAR, TIMESTAMP, BOOLEAN, Float, text
import jwt
import hashlib
from schemas import User,UserCreate,UserMockCreate
from models import UserModel,AreaModel,CellModel
# OAuth2 的 Bearer Token 方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
# 配置
SECRET_KEY = "mysaasfad435435dggfyf4556dsfecretkey"  # 你的密钥
ALGORITHM = "HS256"          # 加密算法
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 访问令牌过期时间
 
class LoginFrom(BaseModel):
    username: str
    password: str

class AdminModel(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32),index=True)
    avatar=Column(String(64))
    introduction=Column(String(128))
    password = Column(String(64), comment='密码')
    disabled= Column(BOOLEAN,comment='是否禁用')
    roles = Column(String,comment='用户角色')
    class Config:
        from_attributes = True

class AdminUser(BaseModel):
    id:int
    name:str
    introduction:str
    avatar:str
    password:str
    roles:str
    disabled: Optional[bool] = None

# Token 模型
class ResToken(BaseModel):
    code:int
    token: str
    token_type: str
class UserRes(BaseModel):
    code:int
    data: AdminUser

class SearchItem(BaseModel):
      name:str

class SearchData(BaseModel):
      items:list[SearchItem]
     
class SearchRes(BaseModel):
    code:int
    data: SearchData


def hash_password(password:str):
    # 使用SHA-256进行密码散列
    hashed_password = hashlib.sha256(password.encode('utf-8'))
    return hashed_password.hexdigest()

# 校验密码的简单实现
def verify_password(plain_password, hashed_password):
    return plain_password == hashed_password  # 直接比较（真实应用中应使用哈希）
 
# 获取用户信息
def get_user(name: str, db: Session = Depends(get_db)):
     if name is None:
        return None
     user = db.query(AdminModel).filter(AdminModel.name == name).first()
     return user
 
def getDefaultUser(name:str):
    if(name=="yijin" ):
        external_data = { 'id': 0,'password':'','avatar': 'https://i2.hdslb.com/bfs/face/9d7fdd3f20a7fd542dd3b4c93b471368c1428cad.jpg@96w_96h.avif','disabled':False,'introduction':'管理者','name':'yijin','roles':'["admin"]'}
        return AdminUser(**external_data)
    if(name=="admin" ):
        external_data = { 'id': 1,'password':'','avatar': 'https://i2.hdslb.com/bfs/face/60b84f456a52e3ef91cc2ccdbe87ae5f9fa36012.jpg@96w_96h.avif','disabled':False,'introduction':'管理者','name':'admin','roles':'["admin"]'}
        return AdminUser(**external_data)
    

# 用户认证
def authenticate_user(username: str, password: str):
    print("authenticate_user username="+username+",password="+password)
    if username=="yijin" and password=="yi3634132":
        return getDefaultUser(username)
    if username=="admin" and password=="123456789":
        return getDefaultUser(username)
    user = get_user(username)
    if(user is None):
        return False
    
    if not verify_password(hash_password(password), user["password"]):
        return False
    return user
 
# 创建访问令牌
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def checkToken(token: str ):
    payload = jwt.decode(token.replace('Bearer ',''), SECRET_KEY, algorithms=[ALGORITHM])
    name = payload.get("sub")
    print("checkToken name="+name)
    if name=="yijin" or name=="admin":
       return getDefaultUser(name)

    user = get_user(name)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user   


def searchUser(name: str,db: Session = Depends(get_db)):
    if name=="yijin" or name=="admin":
        return [{"name":name}]
    if name is None:
        return None
    return db.query(AdminModel).filter(AdminModel.name.like(f"%{name}%")).all()


# 获取单个用户
@app.get("/admin/users/{user_id}")
def readUser(user_id: int,token: str = Header(..., alias="Authorization"), db: Session = Depends(get_db)):
    checkToken(token)
    query = db.query(UserModel,AreaModel.name.label('area'),CellModel.name.label('cell')).outerjoin(AreaModel, UserModel.areaId == AreaModel.id).outerjoin(CellModel, UserModel.cellId == CellModel.id)
    row = query.filter(UserModel.id == user_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    item =row[0]
    area=row[1]
    cell=row[2]
    item.area=area
    item.cell=cell
    return {"code":20000,"data":item}

# 登录获取令牌的接口
@app.post("/admin/token", response_model=ResToken)
async def login(form_data: LoginFrom = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.name})
    return {"code":20000,"token": access_token, "token_type": "bearer"}
 


# 受保护的路由，获取当前用户
@app.get("/admin/me", response_model=UserRes)
async def readMe(token: str = Depends(oauth2_scheme)):
    user = checkToken(token)
    return {"code": 20000, "data": user}

@app.get("/admin/search/user", response_model=SearchRes)
async def readMe(token: str = Header(..., alias="Authorization")):
    list = searchUser(name)
    if list is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"code": 20000, "data": {"items":list}}

@app.get("/admin/logout", response_model=AdminUser)
async def logout(token: str = Depends(oauth2_scheme)):
    user = checkToken(token)
    access_token = create_access_token(data={"sub": user.name},expires_delta=timedelta(minutes=0))
    return {"token": access_token, "token_type": "bearer"}

@app.post("/admin/addmockuser")
def addMockUser(user:UserMockCreate= Depends(), token: str = Header(..., alias="Authorization"),db: Session = Depends(get_db)):
    checkToken(token)
    adddatetime=datetime.now()
    time=adddatetime.timestamp()
    # 创建新用户
    new_user = UserModel(nick_name=user.nick_name,
                         union_id=str(time),
                         open_id=str(time),
                         session_key=str(time),
                         avatar_url=user.avatar_url,
                         gender= user.gender,
                         cellId=user.cellId,
                         cityId=user.cityId,
                         areaId=user.areaId,
                         summary=user.summary,
                         type=0,
                         status=0,
                         created_at=adddatetime,
                         last_login=adddatetime)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"code":20000,"data":new_user}



