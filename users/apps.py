"""
Users app configuration
"""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """
    Configuration for users app
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'User Management'
    
    def ready(self):
        """
        Initialize app when Django starts
        This is called once when Django loads the app
        """
        # Import signals if you have any
        # import users.signals