# serializers.py
from rest_framework import serializers
from sellers.models import Category, Product, Service,SellerProfile, Review
from django.db.models import Avg, Count

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent']  # add more if needed


class ProductSerializer(serializers.ModelSerializer):
    shop = serializers.CharField(source='seller.store_name', read_only=True)
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'original',
            'rating', 'review_count', 'stock_qty', 'stock_sold',
            'image', 'status', 'created_at', 'updated_at', 'category','shop'
        ]


class ServiceSerializer(serializers.ModelSerializer):
    shop = serializers.CharField(source='seller.store_name', read_only=True)
    class Meta:
        model = Service
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'original',
            'duration', 'rating', 'review_count', 'image', 'status',
            'created_at', 'updated_at', 'category','shop'
        ]



class SellerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerProfile
        fields = [
            'id', 'store_name', 'slug', 'description', 'logo', 'banner',
            'location', 'rating', 'review_count', 'positive_feedback_pct',
            'shipping_time', 'response_rate_pct', 'is_verified'
        ]


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_initial = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'user_name', 'user_initial', 'rating', 'comment', 
                  'is_verified_purchase', 'created_at']
        read_only_fields = ['user']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_user_initial(self, obj):
        name = obj.user.get_full_name() or obj.user.username
        return name[0].upper() if name else '?'


class RatingStatsSerializer(serializers.Serializer):
    average_rating = serializers.FloatField()
    total_reviews = serializers.IntegerField()
    stars_5 = serializers.IntegerField()
    stars_4 = serializers.IntegerField()
    stars_3 = serializers.IntegerField()
    stars_2 = serializers.IntegerField()
    stars_1 = serializers.IntegerField()


class ProductDetailSerializer(serializers.ModelSerializer):
    seller = SellerProfileSerializer(read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    rating_stats = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'original',
            'rating', 'review_count', 'stock_qty', 'stock_sold', 'image',
            'status', 'created_at', 'updated_at', 'category',
            'seller', 'reviews', 'rating_stats'
        ]

    def get_rating_stats(self, obj):
        reviews = obj.reviews.all()
        total = reviews.count()
        if total == 0:
            return {
                "average_rating": 0.0,
                "total_reviews": 0,
                "stars_5": 0, "stars_4": 0, "stars_3": 0,
                "stars_2": 0, "stars_1": 0
            }

        avg = reviews.aggregate(Avg('rating'))['rating__avg'] or 0.0
        return {
            "average_rating": round(float(avg), 1),
            "total_reviews": total,
            "stars_5": reviews.filter(rating=5).count(),
            "stars_4": reviews.filter(rating=4).count(),
            "stars_3": reviews.filter(rating=3).count(),
            "stars_2": reviews.filter(rating=2).count(),
            "stars_1": reviews.filter(rating=1).count(),
        }


class ServiceDetailSerializer(serializers.ModelSerializer):
    seller = SellerProfileSerializer(read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    rating_stats = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'original',
            'duration', 'rating', 'review_count', 'image', 'status',
            'created_at', 'updated_at', 'category',
            'seller', 'reviews', 'rating_stats'
        ]

    def get_rating_stats(self, obj):
        reviews = obj.reviews.all()
        total = reviews.count()
        if total == 0:
            return {
                "average_rating": 0.0, "total_reviews": 0,
                "stars_5": 0, "stars_4": 0, "stars_3": 0,
                "stars_2": 0, "stars_1": 0
            }

        avg = reviews.aggregate(Avg('rating'))['rating__avg'] or 0.0
        return {
            "average_rating": round(float(avg), 1),
            "total_reviews": total,
            "stars_5": reviews.filter(rating=5).count(),
            "stars_4": reviews.filter(rating=4).count(),
            "stars_3": reviews.filter(rating=3).count(),
            "stars_2": reviews.filter(rating=2).count(),
            "stars_1": reviews.filter(rating=1).count(),
        }
    



class CategoryWithRatingSerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.CharField()
    avg_rating = serializers.FloatField()
    review_count = serializers.IntegerField()


class ShopDetailSerializer(serializers.ModelSerializer):
    joined_date = serializers.DateTimeField(source='created_at', read_only=True)
    
    # Formatted strings for frontend
    positive_feedback = serializers.SerializerMethodField()
    response_rate = serializers.SerializerMethodField()
    
    # Categories with rating breakdown
    categories = serializers.SerializerMethodField()

    class Meta:
        model = SellerProfile
        fields = [
            'id', 'store_name', 'slug', 'description', 'logo', 'banner',
            'location', 'rating', 'review_count', 'positive_feedback_pct',
            'shipping_time', 'response_rate_pct', 'is_verified',
            'joined_date', 'verification_status',
            'positive_feedback', 'response_rate', 'categories'
        ]

    def get_positive_feedback(self, obj):
        """Returns e.g. "Positive Feedback 98.5%" """
        pct = obj.positive_feedback_pct or 0.0
        return f"Positive Feedback {pct:.1f}%"

    def get_response_rate(self, obj):
        """Returns e.g. "Response Rate 100%" """
        pct = obj.response_rate_pct or 0.0
        return f"Response Rate {pct:.0f}%"

    def get_categories(self, obj):
        """Returns list of categories with avg rating and review count for this seller"""
        # Get all published products of this seller
        products = Product.objects.filter(
            seller=obj, 
            status='PUBLISHED',
            category__isnull=False
        ).select_related('category')

        if not products.exists():
            return []

        # Group by category and calculate stats
        category_stats = {}
        for product in products:
            cat = product.category
            if cat.id not in category_stats:
                category_stats[cat.id] = {
                    'name': cat.name,
                    'slug': cat.slug,
                    'ratings': [],
                    'review_count': 0
                }
            
            # Use product's own rating (which is already average of its reviews)
            if product.rating > 0:
                category_stats[cat.id]['ratings'].append(product.rating)
            category_stats[cat.id]['review_count'] += product.review_count

        # Build final list
        result = []
        for stats in category_stats.values():
            if stats['ratings']:
                avg_rating = round(sum(stats['ratings']) / len(stats['ratings']), 1)
            else:
                avg_rating = 0.0

            result.append({
                'name': stats['name'],
                'slug': stats['slug'],
                'avg_rating': avg_rating,
                'review_count': stats['review_count']
            })

        # Optional: Sort by review_count descending
        result.sort(key=lambda x: x['review_count'], reverse=True)
        return result


class ShopProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'price', 'original', 'rating', 
            'review_count', 'stock_qty', 'image', 'created_at'
        ]


class ShopServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            'id', 'name', 'slug', 'price', 'original', 'rating', 
            'review_count', 'duration', 'image', 'created_at'
        ]