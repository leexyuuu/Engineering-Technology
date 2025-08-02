import jwt
import requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from pydantic import BaseModel
import base64
from sqlalchemy.orm import Session
from base import app,get_db
from fastapi import Depends, HTTPException,Header, status
from datetime import datetime, timedelta
import hmac
import hashlib
from models import Student
import hashlib
import admin
# https://blog.51cto.com/u_16213399/8188051
# https://blog.csdn.net/weixin_52203618/article/details/127130032
# https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/user-login/checkSessionKey.html
# https://developers.weixin.qq.com/miniprogram/dev/api/open-api/user-info/wx.getUserInfo.html

# 微信小程序AppID
appid = 'your_appid'
# 微信小程序AppSecret
appsecret = 'your_appsecret'
access_token = ''
expiresTime = 0
SECRET_KEY = "mysfsfdgd43dsfsdgdfdsg243dsg"  # 你的密钥
ALGORITHM = "HS256"          # 加密算法
ACCESS_TOKEN_EXPIRE_MINUTES = 2400  # 访问令牌过期时间



def sha1(text):
    sha1_hash = hashlib.sha1()
    sha1_hash.update(text.encode('utf-8'))
    return sha1_hash.hexdigest()

# Token 模型
class Token(BaseModel):
    token: str

def isEmptyString(s):
    if s == None or s == "":
        return True
    else:
        return False

# 创建访问令牌
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 获取用户信息
def getUser(id: str, db: Session = Depends(get_db)):
     if id is None:
        return None
     user = db.query(Student).filter(Student.id == id).first()
     return user

# 获取用户信息
def getUserById(id: int, db: Session = Depends(get_db)):
     if id is None:
        return None
     user = db.query(Student).filter(Student.id == id).first()
     return user

def checkToken(token: str ):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    id = payload.get("sub")
    user = getUser(id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def checkUserToken(token: str ):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    id = payload.get("sub")
    user = getUser(id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def checkEdit(token: str,userId:int):
    id=0
    try:
        if token.startswith('Bearer '):
            token = token.replace('Bearer ', '')

    # 尝试执行的代码
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id = int(payload.get("sub"))
    except Exception as e:  # 捕获其他所有异常类型
        # 当其他异常发生时执行的代码
        print(f"发生了一个异常: {e}")
    else:
        # 如果没有异常发生，执行的代码
        print("操作成功完成!")
    if id==0:
        admin.checkToken(token)
        return
    
    if str(id)!=str(userId):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )
  
    user = getUser(id)
    if user is None:
       raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )
def checkUserAndAdmin(token: str):
    id=0
    try:
    # 尝试执行的代码
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id = payload.get("sub")
    except Exception as e:  # 捕获其他所有异常类型
        # 当其他异常发生时执行的代码
        print(f"发生了一个异常: {e}")
    else:
        # 如果没有异常发生，执行的代码
        print("操作成功完成!")
    if id==0:
        admin.checkToken(token)
        return
    user = getUser(id)
    if user is None:
       raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )
def authenticate_user(rawData:str,session_key:str,signature:str):
    return sha1(rawData+session_key) == signature





