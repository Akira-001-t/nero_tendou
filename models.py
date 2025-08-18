import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserMemory(Base):
    __tablename__ = "user_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass

def add_message(user_id: str, role: str, content: str):
    """Add a message to user's memory"""
    db = get_db()
    try:
        # Add new message
        db_message = UserMemory(user_id=str(user_id), role=role, content=content)
        db.add(db_message)
        db.commit()
        
        # Keep only last 20 messages per user
        messages = db.query(UserMemory).filter(
            UserMemory.user_id == str(user_id)
        ).order_by(UserMemory.timestamp.desc()).all()
        
        if len(messages) > 20:
            # Delete oldest messages
            for message in messages[20:]:
                db.delete(message)
            db.commit()
            
    except Exception as e:
        db.rollback()
        print(f"Error adding message to database: {e}")
    finally:
        db.close()

def get_user_memory(user_id: str):
    """Get user's conversation memory"""
    db = get_db()
    try:
        messages = db.query(UserMemory).filter(
            UserMemory.user_id == str(user_id)
        ).order_by(UserMemory.timestamp.asc()).all()
        
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    except Exception as e:
        print(f"Error getting user memory: {e}")
        return []
    finally:
        db.close()

def clear_user_memory(user_id: str):
    """Clear user's conversation memory"""
    db = get_db()
    try:
        db.query(UserMemory).filter(UserMemory.user_id == str(user_id)).delete()
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Error clearing user memory: {e}")
        return False
    finally:
        db.close()

def get_memory_count(user_id: str):
    """Get count of messages in user's memory"""
    db = get_db()
    try:
        count = db.query(UserMemory).filter(UserMemory.user_id == str(user_id)).count()
        return count
    except Exception as e:
        print(f"Error getting memory count: {e}")
        return 0
    finally:
        db.close()