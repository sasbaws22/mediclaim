import aiohttp
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.config import settings

class ElasticMailClient:
    def __init__(self):
        self.api_key = settings.ELASTICMAIL_API_KEY
        self.base_url = "https://api.elasticemail.com/v4"
        self.from_email = settings.ELASTICMAIL_FROM_EMAIL
        self.from_name = settings.ELASTICMAIL_FROM_NAME
        self.headers = {
            "X-ElasticEmail-ApiKey": self.api_key,
            "Content-Type": "application/json"
        }
    
    async def send_email(self, 
                         to_email: str, 
                         subject: str, 
                         html_content: str, 
                         template_id: Optional[str] = None,
                         merge_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send email using ElasticMail API
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            template_id: Optional template ID to use
            merge_data: Optional merge data for template
        
        Returns:
            API response
        """
        endpoint = f"{self.base_url}/emails"
        
        payload = {
            "Recipients": [
                {"Email": to_email}
            ],
            "Content": {
                "Body": [
                    {
                        "ContentType": "HTML",
                        "Charset": "utf-8",
                        "Content": html_content
                    }
                ],
                "From": self.from_email,
                "FromName": self.from_name,
                "Subject": subject
            }
        }
        
        if template_id:
            payload["TemplateID"] = template_id
            
        if merge_data:
            payload["MergeData"] = {
                to_email: merge_data
            }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, headers=self.headers, json=payload) as response:
                return await response.json()
    
    async def send_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        """
        Send SMS using ElasticMail API
        
        Args:
            phone_number: Recipient phone number
            message: SMS message content
        
        Returns:
            API response
        """
        endpoint = f"{self.base_url}/sms"
        
        payload = {
            "To": phone_number,
            "Body": message
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, headers=self.headers, json=payload) as response:
                return await response.json()
    
    async def create_template(self, name: str, subject: str, html_content: str) -> Dict[str, Any]:
        """
        Create email template in ElasticMail
        
        Args:
            name: Template name
            subject: Template subject
            html_content: HTML content of the template
        
        Returns:
            API response
        """
        endpoint = f"{self.base_url}/templates"
        
        payload = {
            "Name": name,
            "Subject": subject,
            "Body": [
                {
                    "ContentType": "HTML",
                    "Charset": "utf-8",
                    "Content": html_content
                }
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, headers=self.headers, json=payload) as response:
                return await response.json()
    
    async def get_templates(self) -> List[Dict[str, Any]]:
        """
        Get all templates from ElasticMail
        
        Returns:
            List of templates
        """
        endpoint = f"{self.base_url}/templates"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, headers=self.headers) as response:
                return await response.json()

elasticmail_client = ElasticMailClient()
