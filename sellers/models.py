from django.db import models
from django.conf import settings
from django.utils.text import slugify

class SellerProfile(models.Model):
    VERIFICATION_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='seller_profile')
    store_name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    logo = models.URLField(blank=True, null=True)
    banner = models.URLField(blank=True, null=True)
    
    # KYC / Business Info
    rc_number = models.CharField(max_length=50, blank=True, null=True)
    business_type = models.CharField(max_length=100, blank=True, null=True)
    business_address = models.TextField(blank=True, null=True)
    id_card = models.URLField(blank=True, null=True)
    business_license = models.URLField(blank=True, null=True)
    
    # Store Performance / Metadata
    location = models.CharField(max_length=255, default='Unknown')
    rating = models.FloatField(default=0.0)
    review_count = models.PositiveIntegerField(default=0)
    positive_feedback_pct = models.FloatField(default=0.0)
    shipping_time = models.CharField(max_length=100, default='1-2 Days')
    response_rate_pct = models.FloatField(default=0.0)
    
    is_verified = models.BooleanField(default=False)
    verification_status = models.CharField(max_length=10, choices=VERIFICATION_STATUS_CHOICES, default='PENDING')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.store_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.store_name

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')

    class Meta:
        verbose_name_plural = 'Categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(models.Model):
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('PUBLISHED', 'Published'),
    )

    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rating = models.FloatField(default=0.0)
    review_count = models.PositiveIntegerField(default=0)
    stock_qty = models.PositiveIntegerField(default=0)
    stock_sold = models.PositiveIntegerField(default=0)
    image = models.URLField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name



class Service(models.Model):
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('PUBLISHED', 'Published'),
    )

    seller = models.ForeignKey(
        "SellerProfile",
        on_delete=models.CASCADE,
        related_name='services'
    )

    category = models.ForeignKey(
        "Category",
        on_delete=models.SET_NULL,
        null=True,
        related_name='services'
    )

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)

    description = models.TextField()

    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Optional service-specific fields
    duration = models.PositiveIntegerField(
        help_text="Duration in minutes",
        null=True,
        blank=True
    )

    # Ratings
    rating = models.FloatField(default=0.0)
    review_count = models.PositiveIntegerField(default=0)

    # Media
    image = models.URLField(blank=True, null=True)

    # Status
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name