from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
from typing import Type, Optional, List, Any, Dict
import logging
from sqlalchemy.ext.declarative import declarative_base
from database import SessionLocal, Base

logger = logging.getLogger(__name__)

class DatabaseHelper:
    def __init__(self):
        self.db = None
    
    @contextmanager
    def get_db(self):
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def create(self, model: Type[Base], data: Dict[str, Any]) -> Optional[Base]:
        """
        Create a new record
        
        Args:
            model: SQLAlchemy model class
            data: Dictionary of column names and values
            
        Returns:
            Created model instance or None if failed
        """
        try:
            with self.get_db() as db:
                item = model(**data)
                db.add(item)
                db.commit()
                db.refresh(item)
                return item
        except SQLAlchemyError as e:
            logger.error(f"Error creating {model.__name__}: {str(e)}")
            return None
    
    def get_all(self, model: Type[Base], filters: Dict = None, order_by: str = None) -> List[Base]:
        """
        Get all records with optional filtering and ordering
        
        Args:
            model: SQLAlchemy model class
            filters: Dictionary of filter conditions
            order_by: Column name to order by (prefix with - for descending)
            
        Returns:
            List of model instances
        """
        try:
            with self.get_db() as db:
                query = db.query(model)
                
                # Apply filters if provided
                if filters:
                    for key, value in filters.items():
                        query = query.filter(getattr(model, key) == value)
                
                # Apply ordering if provided
                if order_by:
                    if order_by.startswith('-'):
                        query = query.order_by(getattr(model, order_by[1:]).desc())
                    else:
                        query = query.order_by(getattr(model, order_by).asc())
                
                return query.all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting all {model.__name__}: {str(e)}")
            return []
    
    def get_single(self, model: Type[Base], id: int) -> Optional[Base]:
        """
        Get a single record by ID
        
        Args:
            model: SQLAlchemy model class
            id: Primary key value
            
        Returns:
            Model instance or None if not found
        """
        try:
            with self.get_db() as db:
                return db.query(model).filter(model.id == id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting {model.__name__} with id {id}: {str(e)}")
            return None
    
    def update(self, model: Type[Base], id: int, data: Dict[str, Any]) -> Optional[Base]:
        """
        Update a record by ID
        
        Args:
            model: SQLAlchemy model class
            id: Primary key value
            data: Dictionary of columns to update
            
        Returns:
            Updated model instance or None if failed
        """
        try:
            with self.get_db() as db:
                item = db.query(model).filter(model.id == id).first()
                if item:
                    for key, value in data.items():
                        setattr(item, key, value)
                    db.commit()
                    db.refresh(item)
                    return item
                return None
        except SQLAlchemyError as e:
            logger.error(f"Error updating {model.__name__} with id {id}: {str(e)}")
            return None
    
    def delete(self, model: Type[Base], id: int) -> bool:
        """
        Delete a record by ID
        
        Args:
            model: SQLAlchemy model class
            id: Primary key value
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            with self.get_db() as db:
                item = db.query(model).filter(model.id == id).first()
                if item:
                    db.delete(item)
                    db.commit()
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Error deleting {model.__name__} with id {id}: {str(e)}")
            return False
    
    def get_filtered(self, model: Type[Base], **kwargs) -> List[Base]:
        """
        Get records with dynamic filtering
        
        Args:
            model: SQLAlchemy model class
            **kwargs: Filter conditions as keyword arguments
            
        Returns:
            List of model instances
        """
        try:
            with self.get_db() as db:
                query = db.query(model)
                for key, value in kwargs.items():
                    query = query.filter(getattr(model, key) == value)
                return query.all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting filtered {model.__name__}: {str(e)}")
            return []