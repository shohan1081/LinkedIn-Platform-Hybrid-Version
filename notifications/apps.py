from django.apps import AppConfig
import firebase_admin
from firebase_admin import credentials
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    def ready(self):
        """
        Initialize Firebase Admin SDK when the app is ready.
        """
        # Only initialize if it hasn't been initialized already
        if not firebase_admin._apps:
            cred_path = getattr(settings, 'FIREBASE_APP_CREDENTIALS', None)
            
            if cred_path and os.path.exists(cred_path):
                try:
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                    logger.info("Firebase Admin SDK initialized successfully.")
                except Exception as e:
                    logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
            else:
                logger.warning(
                    f"Firebase credentials not found at {cred_path}. "
                    "Push notifications using Firebase Admin SDK will not work."
                )
