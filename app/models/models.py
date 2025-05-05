from datetime import datetime, date
import uuid
from typing import List, Optional

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, Float, DateTime, Date, Enum, JSON
from typing import List, Optional,Dict
from sqlmodel import Column, Field, Relationship, SQLModel,select,String
import sqlalchemy.dialects.postgresql as pg
from sqlmodel.ext.asyncio.session import AsyncSession

# Define enum values as strings for better compatibility
class UserRole:
    POLICYHOLDER = "POLICYHOLDER"
    HR = "HR"
    CUSTOMER_SERVICE = "CUSTOMER_SERVICE"
    CLAIMS = "CLAIMS"
    MD = "MD"
    FINANCE = "FINANCE"
    ADMIN = "ADMIN" 
    USER = "USER"

class ClaimStatus:
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW_CS = "UNDER_REVIEW_CS"
    UNDER_REVIEW_CLAIMS = "UNDER_REVIEW_CLAIMS"
    PENDING_MD_APPROVAL = "PENDING_MD_APPROVAL"
    APPROVED = "APPROVED"
    PARTIALLY_APPROVED = "PARTIALLY_APPROVED"
    REJECTED = "REJECTED"
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"

class ReviewType:
    CUSTOMER_SERVICE = "CUSTOMER_SERVICE"
    CLAIMS = "CLAIMS"
    MD = "MD"

class ReviewDecision:
    APPROVED = "APPROVED"
    PARTIALLY_APPROVED = "PARTIALLY_APPROVED"
    REJECTED = "REJECTED"
    NEEDS_MORE_INFO = "NEEDS_MORE_INFO"

class ReviewItemStatus:
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class PaymentStatus:
    SCHEDULED = "SCHEDULED"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"

class NotificationType:
    EMAIL = "EMAIL"
    SMS = "SMS"
    IN_APP = "IN_APP"

class AuditAction:
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    PAYMENT = "PAYMENT"
    STATUS_CHANGE = "STATUS_CHANGE"


class User(SQLModel,table=True):
    __tablename__ = "users"

    id : uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    email : Optional[str] = Field(default=None,nullable=False )
    hashed_password: Optional[str] = Field(default=None)
    full_name: Optional[str] = Field(default=None)
    role: Optional[str] = Field(default=None)
    is_active : bool = Field( default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at : datetime = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})
    # Relationships
    policies:"Policy" = Relationship(back_populates="policyholder",sa_relationship_kwargs={"lazy": "selectin"})
    reviews:"Review" = Relationship(back_populates="reviewer",sa_relationship_kwargs={"lazy": "selectin"})
    payments:"Payment" = Relationship(back_populates="processed_by",sa_relationship_kwargs={"lazy": "selectin"})
    notifications:"Notification" = Relationship(back_populates="user",sa_relationship_kwargs={"lazy": "selectin"})
    audit_logs:"AuditLog" = Relationship(back_populates="user",sa_relationship_kwargs={"lazy": "selectin"})

class Employer(SQLModel,table=True):
    __tablename__ = "employers"

    id : uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    name :str = Field(default=None,nullable=False )
    contact_person :str = Field(default=None,nullable=False )
    contact_email  :str = Field(default=None,nullable=False )
    contact_phone  :str = Field(default=None,nullable=False )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})

    # Relationships
    policies:"Policy" = Relationship(back_populates="employer",sa_relationship_kwargs={"lazy": "selectin"})

class Policy(SQLModel,table=True):
    __tablename__ = "policies"

    id  : uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    member_number :str = Field(default=None,unique=True,nullable=False )
    plan_type  :str = Field(default=None,nullable=False ) 
    policyholder_id :Optional[uuid.UUID] =  Field( nullable=True, foreign_key="users.id",default=None)
    employer_id:Optional[uuid.UUID] =  Field( nullable=True, foreign_key="employers.id",default=None)
    start_date: datetime = Field(default_factory=datetime.now)
    end_date: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field( default=True)
    created_at:datetime = Field(default_factory=datetime.now)
    updated_at:datetime = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})

    # Relationships
    policyholder:User = Relationship(back_populates="policies",sa_relationship_kwargs={"lazy": "selectin"})
    employer:"Employer" = Relationship(back_populates="policies",sa_relationship_kwargs={"lazy": "selectin"})
    claims:"Claim" = Relationship(back_populates="policies",sa_relationship_kwargs={"lazy": "selectin"})

class Claim(SQLModel,table=True):
    __tablename__ = "claims"

    id   : uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    reference_number:str = Field(unique=True, nullable=False)
    policy_id:Optional[uuid.UUID] =  Field( nullable=True, foreign_key="policies.id",default=None)
    hospital_pharmacy:str = Field(nullable=False)
    reason:str = Field(nullable=False)
    requested_amount:float= Field(nullable=False)
    approved_amount:float = Field(nullable=True)
    status:str = Field(nullable=False, default=ClaimStatus.SUBMITTED)
    submission_date:datetime = Field(default=datetime.now)
    created_at:datetime = Field(default_factory=datetime.now)
    updated_at:datetime = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})

    # Relationships
    policies:Policy = Relationship(back_populates="claims",sa_relationship_kwargs={"lazy": "selectin"})
    attachments:"ClaimAttachment" = Relationship(back_populates="claim",sa_relationship_kwargs={"lazy": "selectin"})
    reviews:"Review" = Relationship(back_populates="claim",sa_relationship_kwargs={"lazy": "selectin"})
    payments:"Payment" = Relationship(back_populates="claim",sa_relationship_kwargs={"lazy": "selectin"})
    notifications:"Notification" = Relationship(back_populates="claim",sa_relationship_kwargs={"lazy": "selectin"})

class ClaimAttachment(SQLModel,table=True):
    __tablename__ = "claim_attachments"

    id  : uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    claim_id :Optional[uuid.UUID] =  Field( nullable=True, foreign_key="claims.id",default=None)
    file_name:str = Field(nullable=False)
    file_path:str = Field(nullable=False)
    file_type:str = Field(nullable=False)
    uploaded_at:datetime = Field(default=datetime.now)

    # Relationships
    claim:Claim = Relationship(back_populates="attachments",sa_relationship_kwargs={"lazy": "selectin"})

class Review(SQLModel,table=True):
    __tablename__ = "reviews"

    id  : uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    claim_id:Optional[uuid.UUID] =  Field( nullable=True, foreign_key="claims.id",default=None)
    reviewer_id:Optional[uuid.UUID] =  Field( nullable=True, foreign_key="users.id",default=None)
    review_type:str = Field(nullable=False)
    comments:str = Field(nullable=True)
    decision:str = Field(nullable=False)
    rejection_reason:str = Field(nullable=True)
    reviewed_at:datetime = Field(default_factory=datetime.now)
    created_at:datetime = Field(default_factory=datetime.now)
    updated_at:datetime = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})

    # Relationships
    claim: Claim= Relationship(back_populates="reviews",sa_relationship_kwargs={"lazy": "selectin"})
    reviewer:User = Relationship(back_populates="reviews",sa_relationship_kwargs={"lazy": "selectin"})
    review_items:"ReviewItem" = Relationship(back_populates="review",sa_relationship_kwargs={"lazy": "selectin"})

class ReviewItem(SQLModel,table=True):
    __tablename__ = "review_items"

    id : uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    review_id :Optional[uuid.UUID] =  Field( nullable=True, foreign_key="reviews.id",default=None)
    item_name:str = Field(nullable=False)
    requested_amount:float = Field(nullable=False)
    approved_amount:float = Field(nullable=False)
    status:str = Field(nullable=False)
    rejection_reason:str = Field(nullable=True)
    created_at:datetime = Field(default_factory=datetime.now)
    updated_at:str = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})

    # Relationships
    review:Review = Relationship(back_populates="review_items",sa_relationship_kwargs={"lazy": "selectin"})

class Payment(SQLModel,table=True):
    __tablename__ = "payments"

    id: uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    claim_id  :Optional[uuid.UUID] =  Field( nullable=True, foreign_key="claims.id",default=None)
    invoice_number:str = Field(nullable=False)
    payment_amount:float = Field(nullable=False)
    payment_date:date = Field(nullable=False)
    payment_status:str = Field(nullable=False, default=PaymentStatus.SCHEDULED)
    processed_by_id :Optional[uuid.UUID] =  Field( nullable=True, foreign_key="users.id",default=None)
    created_at:datetime = Field(default_factory=datetime.now)
    updated_at:datetime = Field(default_factory=datetime.now,sa_column_kwargs={"onupdate": datetime.now})

    # Relationships
    claim:Claim = Relationship(back_populates="payments",sa_relationship_kwargs={"lazy": "selectin"})
    processed_by:User = Relationship(back_populates="payments",sa_relationship_kwargs={"lazy": "selectin"})

class Notification(SQLModel,table=True):
    __tablename__ = "notifications"

    id : uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    user_id :Optional[uuid.UUID] =  Field( nullable=True, foreign_key="users.id",default=None)
    claim_id :Optional[uuid.UUID] =  Field( nullable=True, foreign_key="claims.id",default=None)
    title:str = Field(nullable=False)
    message:str = Field(nullable=False)
    notification_type:str = Field(nullable=False)
    is_read:bool = Field(default=False)
    created_at:datetime = Field(default_factory=datetime.now)
    updated_at:datetime = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})

    # Relationships
    user:User = Relationship(back_populates="notifications",sa_relationship_kwargs={"lazy": "selectin"})
    claim:Claim = Relationship(back_populates="notifications",sa_relationship_kwargs={"lazy": "selectin"})

class AuditLog(SQLModel,table=True):
    __tablename__ = "audit_logs"

    id  : uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    user_id :Optional[uuid.UUID] =  Field( nullable=True, foreign_key="users.id",default=None)
    action:str = Field(nullable=False)
    entity_type:str = Field(nullable=False)
    entity_id :Optional[uuid.UUID] =  Field( nullable=True,default=None)
    details:str = Field(sa_column=Column(JSON, nullable=False))
    ip_address:str = Field(nullable=True)
    created_at:datetime= Field(default_factory=datetime.now)

    # Relationships
    user:User = Relationship(back_populates="audit_logs",sa_relationship_kwargs={"lazy": "selectin"})
