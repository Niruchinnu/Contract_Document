from sqlalchemy import Column, Integer, String, JSON, TIMESTAMP, func, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

 # Added role column with default as 'user'

class Revision(Base):
    __tablename__ = "revisions"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    revision = Column(Integer, nullable=False)
    data = Column(JSON, nullable=False)
    diff = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    uploaded_by = Column(Integer, ForeignKey("user.id"), nullable=False)
    confidence_score = Column(Float, nullable=True)

    uploader = relationship("User", back_populates="revisions")


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    role = Column(String(20))
    created_at = Column(TIMESTAMP, server_default=func.now())
    created_by = Column(Integer,nullable=True)
    revisions = relationship("Revision", back_populates="uploader")

