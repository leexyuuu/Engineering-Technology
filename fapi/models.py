from sqlalchemy import Column, Text, Integer,String,Date,DateTime,VARCHAR, TIMESTAMP, BOOLEAN, Float, text
from database import Base



class RoleModel(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(32), index=True, comment='key')
    description = Column(String(128), index=True, comment='描述')
    name = Column(String(32), index=True, comment='名字')

class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    union_id = Column(String(64),unique=True, comment='微信开放平台下的用户唯一标识')
    open_id = Column(String(64),unique=True, comment='微信openid')
    nick_name = Column(String(32), index=True, comment='昵称')
    avatar_url = Column(String(255), server_default=text("''"), comment='头像')
    summary=Column(String,server_default=text("''"))
    session_key= Column(String,server_default=text("''"))
    cityId=Column(Integer,index=True)
    areaId=Column(Integer,index=True)
    cellId=Column(Integer,index=True)
    gender=Column(Integer,server_default=text("'0'"), comment='状态；0:未知 1:男 2:女')
    birth=Column(Date, comment='生日')
    phone = Column(String(11), comment='手机号')
    wechat=Column(String(30), comment='微信号')
    type=Column(Integer,index=True)
    status = Column(String(64), server_default=text("'show'"))
    last_login = Column(TIMESTAMP, comment='上次登录时间')
    delete_at = Column(TIMESTAMP, comment='删除时间')
    created_at = Column(TIMESTAMP, comment='创建时间')
    updated_at = Column(TIMESTAMP, comment='更新时间')
    address=Column(String,server_default=text("''"))

class CellModel(Base):
    __tablename__ = "cells"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32),index=True)
    summary=Column(String)
    icon=Column(String(255), server_default=text("''"), comment='icon')
    index=Column(Integer)
    status= Column(String(32),server_default=text("'show'"),index=True)
    cityId=Column(Integer)
    areaId=Column(Integer)

class AreaModel(Base):
    __tablename__ = "areas"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32),index=True)
    summary=Column(String)
    icon=Column(String(255), server_default=text("''"), comment='icon')
    index=Column(Integer)
    status= Column(String(32),server_default=text("'show'"),index=True)
    cityId=Column(Integer)

class CityModel(Base):
    __tablename__ = "citys"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32),index=True)
    summary=Column(String)
    icon=Column(String(255), server_default=text("''"), comment='icon')
    index=Column(Integer)
    status= Column(String(32),server_default=text("'show'"),index=True)

class ContentModel(Base):
    __tablename__ = "contents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content=Column(String)
    timestamp=Column(TIMESTAMP)
    startTime=Column(TIMESTAMP)
    endTime=Column(TIMESTAMP)
    updateTime=Column(TIMESTAMP)
    comment_disabled=Column(BOOLEAN)
    userId=Column(Integer,index=True)
    type=Column(Integer,index=True)
    like_count=Column(Integer)
    collect_count=Column(Integer)
    images=Column(String)
    cityId=Column(Integer,index=True)
    cellId=Column(Integer,index=True)
    areaId=Column(Integer,index=True)
    address=Column(String)
    extras=Column(String)
    labels=Column(String)
    status= Column(String(32),server_default=text("'show'"),index=True)

class CommentModel(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    content=Column(String)
    contentId=Column(Integer,index=True)
    timestamp=Column(TIMESTAMP)
    isAutor=Column(BOOLEAN)
    updateTime=Column(TIMESTAMP)
    userId=Column(Integer,index=True)
    top=Column(BOOLEAN,index=True)
    images=Column(String)
    status= Column(String(32),server_default=text("'show'"),index=True)

class MessageModel(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    content=Column(String)
    value=Column(Integer,index=True)
    timestamp=Column(TIMESTAMP)
    ready=Column(BOOLEAN)
    fromUserId=Column(Integer)
    userId=Column(Integer,index=True)
    type=Column(Integer,index=True)
    images=Column(String)
    
class MessageBoxModel(Base):
    __tablename__ = "messagegroups"
    id = Column(Integer, primary_key=True, index=True)
    content=Column(String)
    value=Column(Integer,index=True)
    timestamp=Column(TIMESTAMP)
    userId=Column(Integer,index=True)
    type=Column(Integer,index=True)
    count=Column(Integer)
    images=Column(String)

class LikeModel(Base):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True, index=True)
    value=Column(Integer,index=True)
    timestamp=Column(TIMESTAMP)
    userId=Column(Integer,index=True)
    type=Column(Integer,index=True)

class ReplyModel(Base):
    __tablename__ = "replys"
    id = Column(Integer, primary_key=True, index=True)
    content=Column(String)
    commentId=Column(Integer,index=True)
    contentId=Column(Integer)
    timestamp=Column(TIMESTAMP)
    userId=Column(Integer,index=True)
    isAuthor=Column(BOOLEAN)
    atUserId=Column(Integer)
    images=Column(String)
    status= Column(String(32),server_default=text("'show'"),index=True)
    




