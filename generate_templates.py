import os

BASE_DIR = "/home/hackerdev/projects/personal/jefadoback/templates/emails"

templates = {
    "customers/order_confirmation.html": """{% extends "emails/base.html" %}
{% block content %}
<h2>Order Confirmation</h2>
<p>Hi {{ name }},</p>
<p>Thank you for shopping with Jefado! We've received your order <strong>#{{ order_id }}</strong> and it is now being processed.</p>
<table class="data-table">
    <thead>
        <tr>
            <th>Item</th>
            <th>Qty</th>
            <th>Price</th>
        </tr>
    </thead>
    <tbody>
        {% for item in items %}
        <tr>
            <td>{{ item.name }}</td>
            <td>{{ item.quantity }}</td>
            <td>{{ item.price }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
<p><strong>Total: {{ total_amount }}</strong></p>
<div class="button-container">
    <a href="{{ order_url }}" class="button">View Order Details</a>
</div>
<p>We'll send you another email when your order ships.</p>
{% endblock %}""",

    "customers/payment_successful.html": """{% extends "emails/base.html" %}
{% block content %}
<h2>Payment Successful</h2>
<p>Hi {{ name }},</p>
<p>We successfully received your payment of <strong>{{ amount }}</strong> for order <strong>#{{ order_id }}</strong>.</p>
<p>Thank you for your purchase!</p>
{% endblock %}""",

    "customers/order_shipped.html": """{% extends "emails/base.html" %}
{% block content %}
<h2>Your Order is on the Way!</h2>
<p>Hi {{ name }},</p>
<p>Great news! Your order <strong>#{{ order_id }}</strong> has been shipped and is on its way to you.</p>
<p><strong>Tracking Number:</strong> {{ tracking_number }}</p>
<div class="button-container">
    <a href="{{ tracking_url }}" class="button">Track Your Package</a>
</div>
{% endblock %}""",

    "customers/out_for_delivery.html": """{% extends "emails/base.html" %}
{% block content %}
<h2>Out for Delivery</h2>
<p>Hi {{ name }},</p>
<p>Your order <strong>#{{ order_id }}</strong> is out for delivery today! Please make sure someone is available at your shipping address to receive it.</p>
{% endblock %}""",

    "customers/order_delivered.html": """{% extends "emails/base.html" %}
{% block content %}
<h2>Order Delivered</h2>
<p>Hi {{ name }},</p>
<p>Your order <strong>#{{ order_id }}</strong> has been delivered. We hope you love your purchase!</p>
<div class="button-container">
    <a href="{{ review_url }}" class="button">Leave a Review</a>
</div>
{% endblock %}""",

    "customers/promotions.html": """{% extends "emails/base.html" %}
{% block content %}
<h2>{{ promo_title }}</h2>
<p>Hi {{ name }},</p>
<p>{{ promo_message }}</p>
<div style="background-color: #f9f9f9; border: 1px dashed #B31217; padding: 15px; text-align: center; margin: 20px 0; border-radius: 4px;">
    Use Code: <span style="font-size: 20px; font-weight: bold; color: #B31217;">{{ promo_code }}</span>
</div>
<div class="button-container">
    <a href="{{ shop_url }}" class="button">Shop Now</a>
</div>
{% endblock %}""",

    "customers/abandoned_cart.html": """{% extends "emails/base.html" %}
{% block content %}
<h2>Did you forget something?</h2>
<p>Hi {{ name }},</p>
<p>We noticed you left some great items in your cart. They are waiting for you!</p>
<div class="button-container">
    <a href="{{ cart_url }}" class="button">Return to Cart</a>
</div>
{% endblock %}""",

    "vendors/new_order_received.html": """{% extends "emails/base.html" %}
{% block content %}
<h2>New Order Received!</h2>
<p>Hi {{ vendor_name }},</p>
<p>You have received a new order <strong>#{{ order_id }}</strong>.</p>
<p>Please review the order details and start processing it as soon as possible.</p>
<div class="button-container">
    <a href="{{ dashboard_url }}" class="button">View Dashboard</a>
</div>
{% endblock %}""",

    "vendors/new_message.html": """{% extends "emails/base.html" %}
{% block content %}
<h2>New Customer Message</h2>
<p>Hi {{ vendor_name }},</p>
<p>You have received a new message from a customer regarding <strong>{{ subject }}</strong>.</p>
<div style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid #B31217; margin: 20px 0;">
    <p><em>"{{ message_preview }}"</em></p>
</div>
<div class="button-container">
    <a href="{{ inbox_url }}" class="button">Reply to Message</a>
</div>
{% endblock %}""",

    "vendors/product_approval.html": """{% extends "emails/base.html" %}
{% block content %}
<h2>Product Update: {{ status }}</h2>
<p>Hi {{ vendor_name }},</p>
<p>Your product <strong>{{ product_name }}</strong> has been <strong>{{ status }}</strong> by the admin team.</p>
{% if feedback %}
<p><strong>Feedback:</strong> {{ feedback }}</p>
{% endif %}
{% endblock %}""",

    "vendors/low_stock.html": """{% extends "emails/base.html" %}
{% block content %}
<h2>Low Stock Alert</h2>
<p>Hi {{ vendor_name }},</p>
<p>This is an automated alert to let you know that the stock for <strong>{{ product_name }}</strong> is running low.</p>
<p><strong>Current Stock:</strong> {{ current_stock }}</p>
<div class="button-container">
    <a href="{{ product_url }}" class="button">Update Inventory</a>
</div>
{% endblock %}""",

    "vendors/new_review.html": """{% extends "emails/base.html" %}
{% block content %}
<h2>New Review Received</h2>
<p>Hi {{ vendor_name }},</p>
<p>A customer just left a {{ rating }}-star review on your product <strong>{{ product_name }}</strong>.</p>
<div style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid #B31217; margin: 20px 0;">
    <p><em>"{{ review_text }}"</em></p>
</div>
{% endblock %}""",

    "vendors/payout_processed.html": """{% extends "emails/base.html" %}
{% block content %}
<h2>Payout Processed</h2>
<p>Hi {{ vendor_name }},</p>
<p>Good news! Your recent payout of <strong>{{ amount }}</strong> has been successfully processed and transferred to your registered account.</p>
<p>Please note that it may take some time to reflect in your bank account depending on your bank's processing times.</p>
{% endblock %}""",

    "admins/new_vendor.html": """{% extends "emails/base.html" %}
{% block content %}
<h2>New Vendor Registration</h2>
<p>Hello Admin,</p>
<p>A new vendor has registered on the platform and is pending approval.</p>
<p><strong>Store Name:</strong> {{ store_name }}</p>
<p><strong>Vendor Email:</strong> {{ vendor_email }}</p>
<div class="button-container">
    <a href="{{ admin_url }}" class="button">Review Vendor</a>
</div>
{% endblock %}""",

    "admins/failed_payment.html": """{% extends "emails/base.html" %}
{% block content %}
<h2>Payment Failure Alert</h2>
<p>Hello Admin,</p>
<p>A payment failure was detected on the platform.</p>
<p><strong>Order ID:</strong> {{ order_id }}</p>
<p><strong>Customer:</strong> {{ customer_email }}</p>
<p><strong>Amount:</strong> {{ amount }}</p>
<p><strong>Reason:</strong> {{ error_message }}</p>
{% endblock %}""",

    "admins/vendor_support.html": """{% extends "emails/base.html" %}
{% block content %}
<h2>Vendor Support Request</h2>
<p>Hello Admin,</p>
<p>A vendor has submitted a new support request.</p>
<p><strong>Vendor:</strong> {{ vendor_name }}</p>
<p><strong>Subject:</strong> {{ subject }}</p>
<div style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid #B31217; margin: 20px 0;">
    <p><em>"{{ message }}"</em></p>
</div>
{% endblock %}""",

    "admins/fraud_alert.html": """{% extends "emails/base.html" %}
{% block content %}
<h2>CRITICAL: Fraud Alert</h2>
<p>Hello Admin,</p>
<p>Suspicious activity has been detected on the platform.</p>
<p><strong>Type:</strong> {{ alert_type }}</p>
<p><strong>Details:</strong> {{ details }}</p>
<p><strong>User involved:</strong> {{ user_email }}</p>
<div class="button-container">
    <a href="{{ admin_url }}" class="button">Investigate Now</a>
</div>
{% endblock %}"""
}

for rel_path, content in templates.items():
    full_path = os.path.join(BASE_DIR, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)

print("All templates created successfully.")
