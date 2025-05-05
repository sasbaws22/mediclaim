from typing import List, Optional, Any
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.models.models import User, Claim, NotificationType
from app.utils.elasticmail import elasticmail_client

class NotificationService:
    @staticmethod
    async def send_email_notification(
        to_email: str,
        subject: str,
        html_content: str,
        template_id: Optional[str] = None,
        merge_data: Optional[dict] = None
    ) -> dict:
        """
        Send email notification using ElasticMail
        """
        return await elasticmail_client.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            template_id=template_id,
            merge_data=merge_data
        )
    
    @staticmethod
    async def send_sms_notification(
        phone_number: str,
        message: str
    ) -> dict:
        """
        Send SMS notification using ElasticMail
        """
        return await elasticmail_client.send_sms(
            phone_number=phone_number,
            message=message
        )
    
    @staticmethod
    async def create_in_app_notification(
        db: Session,
        user_id: str,
        title: str,
        message: str,
        claim_id: Optional[str] = None
    ) -> Any:
        """
        Create in-app notification in database
        """
        from app.models.models import Notification
        
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=NotificationType.IN_APP,
            is_read=False
        )
        
        if claim_id:
            notification.claim_id = claim_id
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        return notification
    
    @staticmethod
    async def notify_claim_submission(
        background_tasks: BackgroundTasks,
        db: Session,
        claim: Claim,
        policyholder: User,
        hr_users: List[User],
        cs_users: List[User]
    ) -> None:
        """
        Send notifications for claim submission
        """
        # Notify policyholder
        if policyholder.email:
            background_tasks.add_task(
                NotificationService.send_email_notification,
                to_email=policyholder.email,
                subject=f"Claim Submission Confirmation - {claim.reference_number}",
                html_content=f"""
                <h1>Claim Submission Confirmation</h1>
                <p>Dear {policyholder.full_name},</p>
                <p>Your claim with reference number <strong>{claim.reference_number}</strong> has been successfully submitted.</p>
                <p>We will review your claim and get back to you as soon as possible.</p>
                <p>Thank you for using our service.</p>
                """
            )
        
        # Create in-app notification for policyholder
        background_tasks.add_task(
            NotificationService.create_in_app_notification,
            db=db,
            user_id=policyholder.id,
            title="Claim Submitted",
            message=f"Your claim with reference number {claim.reference_number} has been successfully submitted.",
            claim_id=claim.id
        )
        
        # Notify HR users
        for hr_user in hr_users:
            if hr_user.email:
                background_tasks.add_task(
                    NotificationService.send_email_notification,
                    to_email=hr_user.email,
                    subject=f"New Claim Submission - {claim.reference_number}",
                    html_content=f"""
                    <h1>New Claim Submission</h1>
                    <p>Dear {hr_user.full_name},</p>
                    <p>A new claim with reference number <strong>{claim.reference_number}</strong> has been submitted by {policyholder.full_name}.</p>
                    <p>Please review the claim at your earliest convenience.</p>
                    """
                )
            
            # Create in-app notification for HR user
            background_tasks.add_task(
                NotificationService.create_in_app_notification,
                db=db,
                user_id=hr_user.id,
                title="New Claim Submission",
                message=f"A new claim with reference number {claim.reference_number} has been submitted by {policyholder.full_name}.",
                claim_id=claim.id
            )
        
        # Notify CS users
        for cs_user in cs_users:
            if cs_user.email:
                background_tasks.add_task(
                    NotificationService.send_email_notification,
                    to_email=cs_user.email,
                    subject=f"New Claim for Review - {claim.reference_number}",
                    html_content=f"""
                    <h1>New Claim for Review</h1>
                    <p>Dear {cs_user.full_name},</p>
                    <p>A new claim with reference number <strong>{claim.reference_number}</strong> has been submitted by {policyholder.full_name} and requires your review.</p>
                    <p>Please review the claim at your earliest convenience.</p>
                    """
                )
            
            # Create in-app notification for CS user
            background_tasks.add_task(
                NotificationService.create_in_app_notification,
                db=db,
                user_id=cs_user.id,
                title="New Claim for Review",
                message=f"A new claim with reference number {claim.reference_number} has been submitted and requires your review.",
                claim_id=claim.id
            )
    
    @staticmethod
    async def notify_claim_status_update(
        background_tasks: BackgroundTasks,
        db: Session,
        claim: Claim,
        policyholder: User,
        new_status: str
    ) -> None:
        """
        Send notifications for claim status update
        """
        status_description = {
            "SUBMITTED": "submitted",
            "UNDER_REVIEW_CS": "under review by Customer Service",
            "UNDER_REVIEW_CLAIMS": "under review by Claims Department",
            "PENDING_MD_APPROVAL": "pending Medical Director approval",
            "APPROVED": "approved",
            "PARTIALLY_APPROVED": "partially approved",
            "REJECTED": "rejected",
            "PENDING_PAYMENT": "pending payment",
            "PAID": "paid"
        }.get(new_status, new_status)
        
        # Notify policyholder
        if policyholder.email:
            background_tasks.add_task(
                NotificationService.send_email_notification,
                to_email=policyholder.email,
                subject=f"Claim Status Update - {claim.reference_number}",
                html_content=f"""
                <h1>Claim Status Update</h1>
                <p>Dear {policyholder.full_name},</p>
                <p>Your claim with reference number <strong>{claim.reference_number}</strong> is now <strong>{status_description}</strong>.</p>
                <p>You can log in to your account to view more details.</p>
                <p>Thank you for your patience.</p>
                """
            )
        
        # Create in-app notification for policyholder
        background_tasks.add_task(
            NotificationService.create_in_app_notification,
            db=db,
            user_id=policyholder.id,
            title="Claim Status Update",
            message=f"Your claim with reference number {claim.reference_number} is now {status_description}.",
            claim_id=claim.id
        )
    
    @staticmethod
    async def notify_payment_scheduled(
        background_tasks: BackgroundTasks,
        db: Session,
        claim: Claim,
        policyholder: User,
        payment_amount: float,
        payment_date: str
    ) -> None:
        """
        Send notifications for payment scheduled
        """
        # Notify policyholder
        if policyholder.email:
            background_tasks.add_task(
                NotificationService.send_email_notification,
                to_email=policyholder.email,
                subject=f"Payment Scheduled - Claim {claim.reference_number}",
                html_content=f"""
                <h1>Payment Scheduled</h1>
                <p>Dear {policyholder.full_name},</p>
                <p>We are pleased to inform you that a payment of <strong>${payment_amount:.2f}</strong> for your claim with reference number <strong>{claim.reference_number}</strong> has been scheduled for <strong>{payment_date}</strong>.</p>
                <p>You can log in to your account to view more details.</p>
                <p>Thank you for your patience.</p>
                """
            )
        
        # Create in-app notification for policyholder
        background_tasks.add_task(
            NotificationService.create_in_app_notification,
            db=db,
            user_id=policyholder.id,
            title="Payment Scheduled",
            message=f"A payment of ${payment_amount:.2f} for your claim with reference number {claim.reference_number} has been scheduled for {payment_date}.",
            claim_id=claim.id
        )

notification_service = NotificationService()
