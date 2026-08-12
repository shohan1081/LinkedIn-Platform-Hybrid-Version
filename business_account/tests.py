from django.test import TestCase
from rest_framework import serializers
from .serializers import BusinessAccountRegistrationSerializer, BusinessAccountLoginSerializer
from .models import BusinessAccount
from django.core.exceptions import ValidationError

class BusinessEmailRestrictionTest(TestCase):
    def test_registration_with_public_email_fails(self):
        data = {
            'email': 'test@gmail.com',
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        }
        serializer = BusinessAccountRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        self.assertEqual(serializer.errors['email'][0], "Only business email addresses are allowed for business accounts. Please use your professional email.")

    def test_registration_with_business_email_succeeds(self):
        data = {
            'email': 'shohan@mycompany.com',
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        }
        serializer = BusinessAccountRegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_model_validation_with_public_email_fails(self):
        account = BusinessAccount(email='test@yahoo.com')
        with self.assertRaises(ValidationError) as cm:
            account.full_clean()
        self.assertIn('email', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['email'][0], "Only business email addresses are allowed for business accounts. Please use your professional email.")

    def test_login_with_public_email_fails(self):
        # Even if we bypass the model check (e.g. force save), the login serializer should block it
        data = {
            'email': 'olduser@gmail.com',
            'password': 'Password123!'
        }
        serializer = BusinessAccountLoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        self.assertEqual(serializer.errors['non_field_errors'][0], "Only business email addresses are allowed for business accounts. Please use your professional email.")


class CustomBusinessCategoryTest(TestCase):
    def test_standard_category_selection(self):
        from .serializers import BusinessAccountProfileRegistrationSerializer
        data = {
            'role_position': 'CEO',
            'business_name': 'Example Corp',
            'industry_category': 'Technology & Software',
            'business_email': 'contact@examplecorp.com'
        }
        serializer = BusinessAccountProfileRegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['industry_category'], 'Technology & Software')

    def test_custom_category_selection_success(self):
        from .serializers import BusinessAccountProfileRegistrationSerializer
        data = {
            'role_position': 'Founder',
            'business_name': 'Quantum Space Tech',
            'industry_category': 'Other (Specify custom)',
            'custom_industry_category': 'Satellite & Aerospace Engineering',
            'business_email': 'contact@quantumspace.com'
        }
        serializer = BusinessAccountProfileRegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['industry_category'], 'Satellite & Aerospace Engineering')

    def test_custom_category_missing_error(self):
        from .serializers import BusinessAccountProfileRegistrationSerializer
        data = {
            'role_position': 'Founder',
            'business_name': 'Quantum Space Tech',
            'industry_category': 'Other (Specify custom)',
            'business_email': 'contact@quantumspace.com'
        }
        serializer = BusinessAccountProfileRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('custom_industry_category', serializer.errors)

