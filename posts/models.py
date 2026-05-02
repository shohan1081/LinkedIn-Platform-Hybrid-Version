from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
import uuid

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Image(models.Model):
    # Generic foreign key to link to either NeedPost or OfferPost
    post_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    post_object_id = models.UUIDField()
    post = GenericForeignKey('post_content_type', 'post_object_id')

    image = models.ImageField(upload_to='post_images/')
    caption = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        if self.post:
            return f"Image for {self.post.title}"
        return f"Image (ID: {self.id})"

class Post(models.Model):
    # Generic foreign key to link to either User or BusinessAccount
    author_content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE, 
        related_name='%(app_label)s_%(class)s_authored_posts', # Dynamic related_name
        related_query_name='%(app_label)s_%(class)s_authored_post_query' # Dynamic related_query_name
    )
    author_object_id = models.UUIDField()
    author = GenericForeignKey('author_content_type', 'author_object_id')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    tags = models.ManyToManyField(Tag, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # This creates a reverse relation manager named 'images' for NeedPost and OfferPost
    images = GenericRelation(Image, content_type_field='post_content_type', object_id_field='post_object_id')

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class NeedPost(Post):
    CATEGORY_CHOICES = [
        ('Technology', 'Technology'),
        ('Logistic', 'Logistic'),
        ('Marketing', 'Marketing'),
        ('Legal', 'Legal'),
        ('Suply Chain', 'Suply Chain'),
        ('Finance', 'Finance'),
        ('Design', 'Design'),
        ('Other', 'Other'),
    ]

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        help_text=_("Required category for the need post")
    )

    class Meta:
        verbose_name = _("Need Post")
        verbose_name_plural = _("Need Posts")

class NeedPostProposal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    need_post = models.ForeignKey(NeedPost, on_delete=models.CASCADE, related_name='proposals')
    
    # Proposer can be User or BusinessAccount
    proposer_content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE,
    )
    proposer_object_id = models.UUIDField()
    proposer = GenericForeignKey('proposer_content_type', 'proposer_object_id')

    subject = models.CharField(max_length=255, blank=True, null=True, help_text=_("Subject of the proposal"))
    message = models.TextField(blank=True, null=True, help_text=_("Cover letter or proposal message"))
    cv_file = models.FileField(upload_to='proposals/cvs/', blank=True, null=True, help_text=_("CV or supporting document (PDF/Image)"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('need_post', 'proposer_content_type', 'proposer_object_id')
        ordering = ['-created_at']

    def __str__(self):
        return f"Proposal for {self.need_post.title} by {self.proposer}"

class OfferPost(Post):
    CATEGORY_CHOICES = [
        ('Technology', 'Technology'),
        ('Logistic', 'Logistic'),
        ('Marketing', 'Marketing'),
        ('Legal', 'Legal'),
        ('Suply Chain', 'Suply Chain'),
        ('Finance', 'Finance'),
        ('Design', 'Design'),
        ('Other', 'Other'),
    ]

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='Other'
    )
    price_range = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("e.g., $10-$50, negotiable, etc.")
    )
    delivery_time = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("e.g., 3-5 days, immediate, etc.")
    )

    class Meta:
        verbose_name = _("Offer Post")
        verbose_name_plural = _("Offer Posts")

class OfferPostProposal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    offer_post = models.ForeignKey(OfferPost, on_delete=models.CASCADE, related_name='proposals')
    
    # Proposer can be User or BusinessAccount
    proposer_content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE,
    )
    proposer_object_id = models.UUIDField()
    proposer = GenericForeignKey('proposer_content_type', 'proposer_object_id')

    subject = models.CharField(max_length=255, blank=True, null=True, help_text=_("Subject of the proposal"))
    message = models.TextField(blank=True, null=True, help_text=_("Message or inquiry about the offer"))
    attachment = models.FileField(upload_to='proposals/attachments/', blank=True, null=True, help_text=_("Any supporting document or requirement brief"))
    budget = models.CharField(max_length=100, blank=True, null=True, help_text=_("Proposed budget (e.g., $100, negotiable)"))
    expected_delivery = models.CharField(max_length=100, blank=True, null=True, help_text=_("Desired timeline or delivery date"))
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('offer_post', 'proposer_content_type', 'proposer_object_id')
        ordering = ['-created_at']

    def __str__(self):
        return f"Proposal for {self.offer_post.title} by {self.proposer}"
