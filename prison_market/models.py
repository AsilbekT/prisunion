from django.db import models
from django.contrib.auth.models import User
from billing.models import Transaction


class Prison(models.Model):
    name = models.CharField(max_length=255, unique=True)
    location = models.CharField(max_length=400)
    capacity = models.IntegerField(
        help_text="Maximum number of prisoners the facility can hold")
    security_level = models.CharField(
        max_length=100, help_text="The security level of the prison, e.g., Minimum, Medium, Maximum")
    contact_info = models.TextField(
        help_text="Contact information for the prison")
    description = models.TextField(
        blank=True, help_text="Any additional information about the prison")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Prisoner(models.Model):
    full_name = models.CharField(max_length=200)
    identification_number = models.CharField(max_length=100, unique=True)
    prison = models.ForeignKey(
        Prison, related_name='prisoners', on_delete=models.CASCADE)
    cell_number = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    profile_image = models.ImageField(
        upload_to="media/prisoners/", blank=True, null=True)

    def __str__(self):
        return self.full_name


class PrisonerContact(models.Model):
    RELATIONSHIP_CHOICES = (
        ('family', 'Family'),
        ('friend', 'Friend'),
        ('lawyer', 'Lawyer'),
        ('other', 'Other'),
    )
    prisoner = models.ForeignKey(
        Prisoner, related_name='prisoner_contact', on_delete=models.CASCADE, null=True, blank=True)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='prisoner_contact', null=True, blank=True)
    prisoner_full_name = models.CharField(
        max_length=200, blank=True, null=True)
    full_name = models.CharField(max_length=200)
    relationship = models.CharField(
        max_length=50, choices=RELATIONSHIP_CHOICES)
    phone_verification_code = models.CharField(
        max_length=6, blank=True, null=True)
    phone_verified = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=20, blank=True, unique=True)
    address = models.TextField(blank=True)
    additional_info = models.TextField(blank=True)
    picture = models.ImageField(upload_to='media/prisoner_contacts/', blank=True,
                                null=True, help_text="Upload a picture for identity verification.")
    is_approved = models.BooleanField(
        default=False, help_text="Indicates whether the contact is approved by the administration")
    push_notification_user_id = models.CharField(max_length=200,
                                                 unique=True, null=True, blank=True)

    def __str__(self):
        return f"{self.full_name} ({self.get_relationship_display()}"


class ProductCategory(models.Model):
    name = models.CharField(max_length=200)
    image = models.ImageField(
        upload_to="media/productcategories/", blank=True, null=True)

    def __str__(self):
        return self.name


class CategoryBanner(models.Model):
    category = models.ForeignKey(
        ProductCategory, related_name="banners", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="media/categorybanners/")
    title = models.CharField(max_length=255, blank=True,
                             help_text="Optional title for the banner.")
    description = models.TextField(
        blank=True, help_text="Optional description for the banner.")
    link = models.URLField(
        blank=True, help_text="Optional link for the banner to direct users.")

    def __str__(self):
        return f"Banner for {self.category.name}"


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    weight = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    image = models.ImageField(upload_to="media/products/")
    category = models.ForeignKey(
        ProductCategory, on_delete=models.CASCADE, related_name='product_category')
    stock = models.PositiveIntegerField()
    restrictions = models.TextField(blank=True)
    is_trending = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('delivered', 'Delivered'),
    )
    prisoner = models.ForeignKey(
        Prisoner, related_name='orders', on_delete=models.CASCADE)
    ordered_by = models.ForeignKey(
        PrisonerContact, related_name='orders', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='pending')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_status = models.CharField(max_length=50, default='pending')
    delivery_confirmation_image = models.ImageField(
        upload_to='media/order_confirmations/', blank=True, null=True, help_text="Upload a picture as proof of delivery.")
    transaction = models.ForeignKey(
        Transaction, related_name='transactions',  on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Order {self.id} for {self.prisoner.full_name}"

    def update_status(self, new_status):
        self.status = new_status
        self.save()


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(
        Product, related_name='order_items', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price_at_time_of_order = models.DecimalField(
        max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} for {self.order}"


class AuditRecord(models.Model):
    action = models.CharField(max_length=200)
    model = models.CharField(max_length=200)
    record_id = models.PositiveIntegerField()
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField()

    def __str__(self):
        return f"{self.action} on {self.model} (ID: {self.record_id}) by {self.changed_by.username}"


class Notification(models.Model):
    recipient = models.ForeignKey(
        PrisonerContact, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return self.title
