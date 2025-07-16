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
from models import UserModel
from schemas import User,UserCreate,UserMockCreate
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
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 访问令牌过期时间



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

def getAccessToken():
    if isEmptyString(access_token)==False and expiresTime>datetime.now().timestamp():
        return  access_token
    
    url = 'https://api.weixin.qq.com/cgi-bin/token'
    params = {
        'grant_type': 'client_credential',
        'appid': appid,
        'secret': appsecret
    }
    response = requests.get(url, params=params)
    data = response.json()
    token = data.get('access_token')
    access_token = ""
    expiresTime = 0
    if isEmptyString(token) == False:
        access_token = token
        expiresTime = datetime.now().timestamp() + int(data.get('expires_in'))
    return access_token


def checksession(openid,session_key):
    url = 'https://api.weixin.qq.com/wxa/checksession'
    accessToken = getAccessToken()
    if isEmptyString(access_token):
        return
    hmac_code = hmac.new(session_key, "",digestmod=hashlib.sha256)
    # 获取HMAC值
    # hmac_sha256_digest = hmac_code.digest()
 
    # 将HMAC值转换为十六进制字符串
    # hmac_sha256_hex = hmac_code.hexdigest()
 
    params = {
        'access_token': accessToken,
        'openid': openid,
        'signature': hmac_code,
        'sig_method': 'hmac_sha256'
    }
    response = requests.get(url, params=params)
    data = response.json()
    errcode = data.get('errcode')
    errmsg = data.get('errmsg')
    return errcode


# 请求微信接口获取openid和session_key
def get_openid_and_session_key(code):

    url = 'https://api.weixin.qq.com/sns/jscode2session'
    
    params = {
        'appid': appid,
        'secret': appsecret,
        'js_code': code,
        'grant_type': 'authorization_code'
    }
    response = requests.get(url, params=params)
    data = response.json()
    openid = data.get('openid')
    session_key = data.get('session_key')
    unionid=data.get('unionid')
    errcode=data.get('errcode')
    errmsg=data.get('errmsg')
    return openid, session_key,unionid

# 解密用户敏感数据
def decrypt_data(session_key, encrypted_data, iv):
    backend = default_backend()
    cipher = Cipher(algorithms.AES(session_key), modes.CBC(iv), backend=backend)
    decryptor = cipher.decryptor()
    decrypted_data = decryptor.update(base64.b64decode(encrypted_data)) + decryptor.finalize()
    return decrypted_data


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
def getUser(unionid: str, db: Session = Depends(get_db)):
     if unionid is None:
        return None
     user = db.query(UserModel).filter(UserModel.union_id == unionid).first()
     return user

# 获取用户信息
def getUserById(id: int, db: Session = Depends(get_db)):
     if id is None:
        return None
     user = db.query(UserModel).filter(UserModel.id == id).first()
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
def checkEdit(token: str,userId:int):
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
    
    if id!=userId:
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


def addUser(rawData:str,openid, session_key,unionid, db: Session = Depends(get_db)):
    data= rawData.json()
    nickName=data.get('nickName')
    gender=data.get('gender')
    avatarUrl=data.get('avatarUrl')
    
    time=datetime.now().timestamp()
    # 创建新用户
    new_user = UserModel(nickName,
                         union_id=unionid,
                         open_id=openid,
                         type=1,
                         session_key=session_key,
                         avatar_url=avatarUrl,
                         gender= gender,
                         status=1,
                         created_at=time,
                         last_login=time)
    new_user.created_at=datetime.now().timestamp()
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
    ""
@app.post("/user/login", response_model=Token)
async def login(userCreate:UserCreate):
    openid, session_key,unionid = get_openid_and_session_key(userCreate.code)
    if isEmptyString(session_key) or isEmptyString(unionid):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if authenticate_user(userCreate.rawData,session_key,userCreate.signature)==False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user=getUser(unionid) 
    if  user == None:
        user=addUser(userCreate.rawData,openid,session_key,unionid)
        ""

  #  decrypted_data = decrypt_data(session_key, userCreate.encrypted_data, userCreate.iv)
   # data = decrypted_data.json()
    # 处理解密后的数据，生成用户的登录态
    # ...
    token = create_access_token(data={"sub": user.id})
    return {"token": token}

def safeUser(user:User):
    user.open_id=""
    user.union_id=""
    user.session_key=""
    user.wechat=""
    user.phone=""
    user.address=""
    return user

def safeUser2(user:User):
    user.open_id=""
    user.union_id=""
    user.session_key=""
    return user


