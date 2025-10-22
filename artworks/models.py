from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings





# 1. Custom User Model
class User(AbstractUser):
    is_artist = models.BooleanField(default=False)
    is_buyer = models.BooleanField(default=True)
    profile_image = models.ImageField(
        upload_to='profile_images/',
        blank=True,
        null=True,
        default='profile_images/default-avatar.png'  # ✅ default image
    )
    location = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    
    def is_profile_complete(self):
        return bool(self.profile_image or self.bio or (self.first_name and self.last_name))

    def __str__(self):
        return self.username


# 2. Artwork
class Artwork(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    )

    SALE_TYPE_CHOICES = (
        ('fixed', 'Fixed Price'),
        ('auction', 'Live Auction'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='artworks/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    sale_type = models.CharField(max_length=20, choices=SALE_TYPE_CHOICES, default='fixed')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sold = models.BooleanField(default=False)

    def __str__(self):
        return self.title
    

   
# 5. Notification
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}"

# 6. Auction Request
class AuctionRequest(models.Model):
     STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),   # 🔹 new status
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

     user = models.ForeignKey(User, on_delete=models.CASCADE)
     title = models.CharField(max_length=255)
     image = models.ImageField(upload_to="auction_requests/")
     reserve_price = models.DecimalField(max_digits=10, decimal_places=2)
     notes = models.TextField(blank=True, null=True)
     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
     created_at = models.DateTimeField(auto_now_add=True)
     

     def __str__(self):
        return f"{self.title} by {self.user.username}"


# Then define Auction below
class Auction(models.Model):
    artwork = models.ForeignKey('Artwork', on_delete=models.CASCADE)
    auction_request = models.OneToOneField('AuctionRequest', on_delete=models.CASCADE, null=True, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    reserve_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    highest_bid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    highest_bidder = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bids_won'
    )
    winner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auction_wins'
    )
    winner_announced = models.BooleanField(default=False)

    def __str__(self):
        return f"Auction for {self.artwork.title} ({self.start_time} → {self.end_time})"

    def is_ended(self):
        
        return timezone.now() > self.end_time

    def announce_winner(self):
       
        if self.is_ended() and not self.winner_announced and self.highest_bidder:
            self.winner = self.highest_bidder  # ✅ This must be a User instance
            self.winner_announced = True
            self.save()
            return self.winner
        return None


    # 4. Bid
class Bid(models.Model):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name="bids")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bids")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-amount"]  # Always order bids from highest to lowest

    def __str__(self):
        return f"{self.user.username} - {self.amount}"
    

     # Cart
class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    artwork = models.ForeignKey('Artwork', on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'artwork')  # prevent duplicates

    def __str__(self):
        return f"{self.user.username} - {self.artwork.title}"
    
class PaymentSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default="PENDING")  # PENDING / PAID / CANCELLED
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.artwork.title} - {self.status}"
    

class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    artwork = models.ForeignKey('Artwork', on_delete=models.CASCADE)
    price = models.FloatField() 
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.artwork.title} - {self.user.username}"



