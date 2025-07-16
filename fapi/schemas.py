from pydantic import BaseModel
from datetime import datetime, timedelta
import time
from typing import Optional, List

class RoleBase(BaseModel):
    key:str
    name:str
    description:str

class RoleUpdate(RoleBase):
     pass
class RoleCreate(RoleBase):
     pass


class Role(RoleBase):
    id: int
    class Config:
        from_attributes = True


class UserMockCreate(BaseModel):
    nick_name : str
    summary:str
    avatar_url : str
    cityId:int
    areaId:int
    cellId:int
    gender:int
   
class UserUpdate(BaseModel):
    id: int
    nick_name : str
    summary:str
    avatar_url : str
    status:int
    cityId:int
    areaId:int
    cellId:int
    gender:int

class User(BaseModel):
    id: int
    union_id:str
    open_id : str
    nick_name : str
    session_key:str
    summary:str
    type:int
    avatar_url : str
    status:int
    cityId:int
    areaId:int
    cellId:int
    gender:int
    birth:str
    address:str
    last_login:int
    delete_at:int
    created_at:int
    updated_at:int
    phone:str
    wechat:str
    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    token : str
   # encryptedData : str
    #iv:str
    rawData:str
    signature:str

# Cell schemas (已存在的代码)
class CellBase(BaseModel):
    """小区基础模型"""
    name: str
    status: Optional[str] = 'show'
    summary: Optional[str] = None
    icon: Optional[str] = None
    index: Optional[int] = None
    cityId: Optional[int] = None
    areaId: Optional[int] = None

class CellCreate(CellBase):
    """创建小区请求模型"""
    pass

class CellUpdate(CellBase):
    """更新小区请求模型"""
    pass

class Cell(CellBase):
    """小区响应模型"""
    id: int

    class Config:
        from_attributes = True


# City schemas
class CityBase(BaseModel):
    """城市基础模型"""
    name: Optional[str] = ''
    summary: Optional[str] = ''
    status: Optional[str] = 'show'
    icon: Optional[str] = ''
    index: Optional[int] = 0

class CityCreate(CityBase):
    """创建城市请求模型"""
    pass

class CityUpdate(CityBase):
    """更新城市请求模型"""
    pass

class City(CityBase):
    """城市响应模型"""
    id: int
    class Config:
        from_attributes = True

# Area schemas
class AreaBase(BaseModel):
    """区域基础模型"""
    name: str
    cityId: int
    status: Optional[str] = 'show'
    index: Optional[int] = None

class AreaCreate(AreaBase):
    """创建区域请求模型"""
    pass

class AreaUpdate(AreaBase):
    """更新区域请求模型"""
    pass

class Area(AreaBase):
    """区域响应模型"""
    id: int

    class Config:
        from_attributes = True

# Content schemas
class ContentBase(BaseModel):
    """内容基础模型"""
    title: str
    content: str
    like_count:int
    collect_count:int
    cityId:int
    cellId:int
    areaId:int
    userId:int
    images:str
    address:str
    extras:str
    labels:str 
    type: Optional[int] = None
    status: Optional[str] = 'show'
    comment_disabled: Optional[bool] = False
    timestamp: Optional[datetime] = None
    startTime: Optional[datetime] = None
    endTime: Optional[datetime] = None
    updateTime: Optional[datetime] = None



class ContentCreate(BaseModel):
    """创建内容请求模型"""
    title: str
    content: Optional[str]=''
    images: Optional[str]=''
    userId:int
    comment_disabled:Optional[bool]=False
    type:int
    status:Optional[str]='show'

class ContentUpdate(BaseModel):
    id: int
    title: str
    content: Optional[str]=''
    images: Optional[str]=''
    userId:int=0
    comment_disabled:Optional[bool]=False
    status:Optional[str]='show'

class Content(ContentBase):
    """内容响应模型"""
    id: int

    class Config:
        from_attributes = True

class CommentBase(BaseModel):
    """内容基础模型"""
    content: str
    userId:int
    contentId:int
    images:str
    isAutor:bool
    status:str
    top:bool
    timestamp: Optional[datetime] = None
    updateTime: Optional[datetime] = None

class CommentCreate(BaseModel):
    """内容基础模型"""
    content: str
    userId:int
    contentId:int
    images:str
    status:str
    top:bool


class CommentUpdate(BaseModel):
    id: int
    content: str
    userId:int
    images:str
    status:str
    top:bool

class Comment(CommentBase):
    """内容响应模型"""
    id: int

    class Config:
        from_attributes = True



class MessageBox(BaseModel):
    id: int
    """内容基础模型"""
    content: str
    userId:int
    fromUserId:int
    value:int
    avatar:str
    images:str
    type:str
    count:int
    timestamp: Optional[datetime] = None
    class Config:
        from_attributes = True
        
class MessageUpdate(BaseModel):
    id: int
    """内容基础模型"""
    content: str
    userId:int
    value:int
    avatar:str
    images:str
    type:str
    count:int
    timestamp: Optional[datetime] = None

class MessageCreate(BaseModel):
    content: str
    userId:int
    value:int
    fromUserId:int
    avatar:str
    images:str
    type:str

class MessageLetter(BaseModel):
    content: str
    images:str
    userId:int

class Message(BaseModel):
    id: int
    content: str
    userId:int
    ready:bool
    value:int
    images:str
    type:str
    timestamp: Optional[datetime] = None
    class Config:
        from_attributes = True

class Like(BaseModel):
    id: int
    userId:int
    value:int
    type:str
    timestamp: Optional[datetime] = None
    class Config:
        from_attributes = True

class Reply(BaseModel):
    id: int
    content: str
    userId:int
    atUserId:int
    contentId:int
    commentId:int
    isAuthor:bool
    images:str
    status:str
    timestamp: Optional[datetime] = None

class ReplyCreate(BaseModel):
    """内容基础模型"""
    content: str
    userId:int
    atUserId:int
    contentId:int
    commentId:int
    images:str
    status:str

class ReplyUpdate(BaseModel):
    id: int
    """内容基础模型"""
    content: str
    images:str
    userId:int
    status:str
    
    
