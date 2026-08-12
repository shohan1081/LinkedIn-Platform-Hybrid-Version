from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.contenttypes.models import ContentType
from users.models import User, UserBlock, UserReport, Follow
from business_account.models import BusinessAccount
from posts.models import NeedPost

class UserProfileOptionsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='password123',
            first_name='John',
            last_name='Doe',
            headline='Software Engineer'
        )
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='password123',
            first_name='Jane',
            last_name='Smith',
            headline='Product Manager'
        )
        self.business = BusinessAccount.objects.create_user(
            email='company@business.com',
            password='password123',
            business_name='TechCorp'
        )

        # Authenticate client as user1
        self.client.force_authenticate(user=self.user1)

    def test_profile_options_payload(self):
        """Test that profile options (three-dot menu metadata) are returned on profile endpoint"""
        url = reverse('users:other-user-profile', kwargs={'pk': str(self.user2.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        profile_options = response.data['data']['profile_options']
        self.assertFalse(profile_options['is_blocked'])
        self.assertIn('share_url', profile_options)
        self.assertIn('copy_link', profile_options)
        self.assertEqual(len(profile_options['available_actions']), 4)

    def test_block_and_unblock_user(self):
        """Test blocking and unblocking another user"""
        url = reverse('users:block-toggle')

        # Block user2
        data = {
            'target_id': str(self.user2.id),
            'target_type': 'user',
            'action': 'block'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertTrue(UserBlock.objects.filter(blocker_object_id=self.user1.id, blocked_object_id=self.user2.id).exists())

        # Unblock user2
        data['action'] = 'unblock'
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(UserBlock.objects.filter(blocker_object_id=self.user1.id, blocked_object_id=self.user2.id).exists())

    def test_blocked_users_list(self):
        """Test listing blocked users"""
        user_ct = ContentType.objects.get_for_model(User)
        UserBlock.objects.create(
            blocker_content_type=user_ct,
            blocker_object_id=self.user1.id,
            blocked_content_type=user_ct,
            blocked_object_id=self.user2.id
        )
        url = reverse('users:blocked-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['id'], str(self.user2.id))

    def test_report_user(self):
        """Test reporting a user profile"""
        url = reverse('users:report-user')
        data = {
            'target_id': str(self.user2.id),
            'target_type': 'user',
            'reason': 'harassment',
            'description': 'Abusive language on post comments'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertTrue(UserReport.objects.filter(reporter_object_id=self.user1.id, target_object_id=str(self.user2.id)).exists())

    def test_profile_share_metadata(self):
        """Test profile share endpoint output"""
        url = reverse('users:profile-share', kwargs={'pk': str(self.user2.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'Jane Smith')
        self.assertIn('share_url', response.data['data'])
        self.assertIn('copy_link', response.data['data'])
