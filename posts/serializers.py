from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from .models import Tag, Image, NeedPost, OfferPost, NeedPostProposal
from users.models import User
from business_account.models import BusinessAccount

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'

class ImageSerializer(serializers.ModelSerializer):
    # Use standard ImageField for output. For input, we'll handle files manually in BasePostSerializer.
    image = serializers.ImageField(required=False) 

    class Meta:
        model = Image
        fields = ['image', 'caption']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and instance.image:
            representation['image'] = request.build_absolute_uri(instance.image.url)
        return representation

class BasePostSerializer(serializers.ModelSerializer):
    author_id = serializers.SerializerMethodField()
    author_type = serializers.SerializerMethodField()
    
    # Nested ImageSerializer for output (read-only)
    images = ImageSerializer(many=True, read_only=True)

    # tags for list input (write_only) - as per LinkedIn style
    tags = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )
    # TagSerializer for output (read_only)
    tags_detail = TagSerializer(many=True, read_only=True, source='tags')

    class Meta:
        model = NeedPost # This will be overridden by subclasses (NeedPostSerializer, OfferPostSerializer)
        fields = [
            'id', 'author_id', 'author_type', 'title', 'description', 
            'tags', 'tags_detail', 'images', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author_id', 'author_type', 'created_at', 'updated_at']

    def get_author_id(self, obj):
        return str(obj.author.id) if obj.author else None

    def get_author_type(self, obj):
        if isinstance(obj.author, User):
            return 'user'
        elif isinstance(obj.author, BusinessAccount):
            return 'business_account'
        return None

    def _handle_tags(self, tag_names, post_instance):
        if tag_names is not None:
            tag_objects = []
            for name in tag_names:
                if name.strip():
                    tag, _ = Tag.objects.get_or_create(name=name.strip().lower())
                    tag_objects.append(tag)
            post_instance.tags.set(tag_objects)

    def create(self, validated_data):
        # Remove 'tags' from validated_data as we handle them manually
        tag_names = validated_data.pop('tags', [])
        
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise ValidationError("Authentication required to create a post.")

        author = request.user
        if isinstance(author, User):
            validated_data['author_content_type'] = ContentType.objects.get_for_model(User)
        elif isinstance(author, BusinessAccount):
            validated_data['author_content_type'] = ContentType.objects.get_for_model(BusinessAccount)
        else:
            raise ValidationError("Authenticated user is neither a User nor a BusinessAccount.")
        validated_data['author_object_id'] = author.id

        post = super().create(validated_data) 

        # Manually handle images from request.FILES
        uploaded_images = request.FILES.getlist('images')
        uploaded_captions = request.data.getlist('images_caption') if request.data.getlist('images_caption') else [''] * len(uploaded_images)

        for i, uploaded_file in enumerate(uploaded_images):
            caption = uploaded_captions[i] if i < len(uploaded_captions) else ''
            Image.objects.create(
                post_content_type=ContentType.objects.get_for_model(post),
                post_object_id=post.id,
                image=uploaded_file,
                caption=caption
            )
        
        self._handle_tags(tag_names, post)
        
        return post

    def update(self, instance, validated_data):
        # Remove 'tags' from validated_data as we handle them manually
        tag_names = validated_data.pop('tags', None)
        
        request = self.context.get('request')

        instance = super().update(instance, validated_data)

        # Manually handle images from request.FILES if 'images' key was present in the request
        if 'images' in request.FILES or ('images' in request.data and not request.FILES.getlist('images')):
            Image.objects.filter(
                post_content_type=ContentType.objects.get_for_model(instance),
                post_object_id=instance.id
            ).delete() # Clear existing images

            uploaded_images = request.FILES.getlist('images')
            uploaded_captions = request.data.getlist('images_caption') if request.data.getlist('images_caption') else [''] * len(uploaded_images)

            for i, uploaded_file in enumerate(uploaded_images):
                caption = uploaded_captions[i] if i < len(uploaded_captions) else ''
                Image.objects.create(
                    post_content_type=ContentType.objects.get_for_model(instance),
                    post_object_id=instance.id,
                    image=uploaded_file,
                    caption=caption
                )
        
        if tag_names is not None:
            self._handle_tags(tag_names, instance)

        return instance

class NeedPostSerializer(BasePostSerializer):
    class Meta(BasePostSerializer.Meta):
        model = NeedPost
        fields = BasePostSerializer.Meta.fields + ['category']

class OfferPostSerializer(BasePostSerializer):
    class Meta(BasePostSerializer.Meta):
        model = OfferPost
        fields = BasePostSerializer.Meta.fields + ['category', 'price_range', 'delivery_time']

class UserAndBusinessPostListSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    author_id = serializers.SerializerMethodField()
    author_type = serializers.SerializerMethodField()
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    tags_detail = TagSerializer(many=True, read_only=True, source='tags')
    images = ImageSerializer(many=True, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    # Common field
    category = serializers.CharField(read_only=True)

    # Specific fields for OfferPost
    post_type = serializers.SerializerMethodField()
    price_range = serializers.CharField(read_only=True)
    delivery_time = serializers.CharField(read_only=True)

    def get_author_id(self, obj):
        return str(obj.author.id) if obj.author else None

    def get_author_type(self, obj):
        if isinstance(obj.author, User):
            return 'user'
        elif isinstance(obj.author, BusinessAccount):
            return 'business_account'
        return None

    def get_post_type(self, obj):
        if isinstance(obj, NeedPost):
            return 'need'
        elif isinstance(obj, OfferPost):
            return 'offer'
        return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if isinstance(instance, NeedPost):
            # Remove OfferPost specific fields for NeedPost
            representation.pop('price_range', None)
            representation.pop('delivery_time', None)
        return representation

class NeedPostProposalSerializer(serializers.ModelSerializer):
    proposer_id = serializers.SerializerMethodField()
    proposer_type = serializers.SerializerMethodField()

    class Meta:
        model = NeedPostProposal
        fields = ['id', 'need_post', 'proposer_id', 'proposer_type', 'subject', 'message', 'cv_file', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'need_post', 'proposer_id', 'proposer_type', 'status', 'created_at', 'updated_at']

    def get_proposer_id(self, obj):
        return str(obj.proposer.id) if obj.proposer else None

    def get_proposer_type(self, obj):
        if isinstance(obj.proposer, User):
            return 'user'
        elif isinstance(obj.proposer, BusinessAccount):
            return 'business_account'
        return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and instance.cv_file:
            representation['cv_file'] = request.build_absolute_uri(instance.cv_file.url)
        return representation
