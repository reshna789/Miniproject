from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import User
from .models import AuctionRequest, Auction, Artwork, Notification, Bid, Cart, PaymentSession
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.utils.timezone import now
from django.utils import timezone
from django.http import JsonResponse,  HttpResponseRedirect
import json
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
from django.contrib.admin.views.decorators import staff_member_required
from decimal import Decimal
from datetime import datetime
from django.db.models import Max
from django.db.models import Count
from .forms import AuctionForm
from django.views.decorators.http import require_POST
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Case, When, Value, IntegerField, Q
from .forms import ProfileForm, FixedArtworkForm
from artworks.models import Artwork
from .models import CartItem








# Use the custom user model
User = get_user_model()



def home(request):
    return render(request, "artworks/index.html")

# Register
def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if password1 != password2:
            messages.error(request, "Passwords don’t match")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('register')

        # Create user using the correct model
        user = User.objects.create_user(username=username, email=email, password=password1)
        user.save()
        messages.success(request, "Account created! Please log in.")
        return redirect('login')

    return render(request, "artworks/register.html")


def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)

            # Check if superuser
            if user.is_superuser:
                return redirect('admindashboard')  # URL name for your admin dashboard
            else:
                return redirect('userdashboard')  # URL name for normal user dashboard

        else:
            messages.error(request, "Invalid username or password")
            return redirect('login')

    return render(request, "artworks/login.html")


def user_dashboard(request):
   # 📨 Count unread notifications
    unread_count = request.user.notifications.filter(is_read=False).count()

    auctions = Auction.objects.select_related('artwork', 'winner').all().order_by('-end_time')

    current_time = timezone.now()

    for auction in auctions:
        # Determine status for current user
        if auction.end_time <= current_time:
            if auction.winner == request.user:
                auction.user_action = 'pay'  # Winner sees Pay button
            else:
                auction.user_action = 'ended'  # Other users see Auction Ended
        else:
            auction.user_action = 'live'  # Ongoing auction

        # Attach highest bid info
        highest_bid = Bid.objects.filter(auction=auction).order_by("-amount").first()
        auction.highest_bid = highest_bid.amount if highest_bid else auction.reserve_price
        auction.highest_bidder = highest_bid.user if highest_bid else None
        auction.is_live = auction.start_time <= current_time <= auction.end_time


    context = {
        'unread_count': unread_count,
        'auctions': auctions,
        'user': request.user,
    }

    return render(request, 'artworks/user_dashboard.html', context)

# Logout
def user_logout(request):
    logout(request)
    return redirect('login')

# Upload artwork (requires login)
@login_required
def upload_artwork(request):
    if request.method == "POST":
        Artwork.objects.create(
            user=request.user,
            title=request.POST['title'],
            description=request.POST.get('description'),
            image=request.FILES['image'],
            price=request.POST['price'],
            sale_type='fixed',
            status='pending'  # ✅ Auto publish
        )
        return redirect('profile_view')

# forgot password

def forgot_password(request):
    return render(request,'artworks/forgot.html')



# fixed sale

# def fixed_sales(request):
#     artworks = Artwork.objects.filter(sale_type='fixed', status='pending')
    
#     unread_count = 0
#     cart_count = 0
#     if request.user.is_authenticated:
#         unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
#         cart_count = CartItem.objects.filter(user=request.user).count()

#     context = {
#         "artworks": artworks,
#         "cart_count": cart_count,
#         "unread_count": unread_count,
#     }
#     return render(request, 'fixed_sales.html', context)
def fixed_sales(request):
    artworks = Artwork.objects.filter(status="pending",sale_type="fixed").annotate(
        is_user_art=Case(
            When(user=request.user, then=1),
            default=0,
            output_field=IntegerField()
        )
    ).order_by('-is_user_art', '-id')  
    context = {
        "artworks": artworks,
        "cart_count": 0,  # Replace with real cart count if available
        "unread_count": 0,  # Replace with notifications
    }
    return render(request, "fixed_sales.html", context)




def fps_uploadform(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        price = request.POST.get("price")
        image = request.FILES.get("image")
        price = Decimal(price) if price else Decimal('0.00')

        Artwork.objects.create(
            user=request.user,
            title=title,
            description=description,
            price=price,
            image=image,
            status="Pending",
            sale_type="fixed",  # 🔹 explicitly set
        )
        return redirect("fixed_sales")
    
    return render(request, "artworks/fps_uploadform.html")


def notifications(request):
    if not request.user.is_authenticated:
        return redirect('login_page')

    # ✅ Fetch all notifications for this user
    user_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    # ✅ Count unread notifications
    unread_count = user_notifications.filter(is_read=False).count()

    context = {
        'notifications': user_notifications,
        'unread_count': unread_count,
    }
    return render(request, 'artworks/notification.html', context)

@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)

    # ✅ Mark it as read
    notification.is_read = True
    notification.save()

    # ✅ Redirect back to notifications page
    return redirect('notifications')


def cart_view(request):
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    context = {
        'unread_count': unread_count
    }
    return render(request, 'artworks/cart.html', context)


def logout_page(request):
    return render(request, "logout.html")



def payment_page(request, artwork_id):
    artwork = get_object_or_404(Artwork, id=artwork_id)

    if request.method == "POST":
        artwork.sold = True   # ✅ Marks sold in DB
        artwork.status = "Sold"
        artwork.save()
        return redirect('fixed_sales')

    context = {"artwork": artwork}
    return render(request, "artworks/payment.html", context)


# def payment_page(request, artwork_id):
#     artwork = get_object_or_404(Artwork, id=artwork_id)
    
#     if request.method == "POST":
#         # After successful payment simulation
#         artwork.sold = True
#         artwork.status = "Sold"
#         artwork.save()
#         return redirect('fixed_sales')  # Redirect to fixed sales

#     context = {"artwork": artwork}
#     return render(request, "artworks/payment.html", context)

def payment_back(request):
    # Redirect to fixed sales page
    return redirect('fixed_sales')


#Auction

def auctions(request):
    unread_count = 0
    if request.user.is_authenticated:
      unread_count = request.user.notifications.filter(is_read=False).count()

    current_time = timezone.now()
    cutoff_time = current_time - timedelta(hours=24)

    
    auctions_list = Auction.objects.filter(
        Q(auction_request__status="approved") | Q(auction_request__isnull=True),
        artwork__sale_type="auction",
        end_time__gte=cutoff_time
    ).order_by('-start_time')

    # Attach highest bid, bidder, and is_live flag
    for auction in auctions_list:
        highest_bid = Bid.objects.filter(auction=auction).order_by("-amount").first()
        auction.highest_bid = highest_bid.amount if highest_bid else auction.reserve_price
        auction.highest_bidder = highest_bid.user if highest_bid else None
        auction.is_live = auction.start_time <= current_time <= auction.end_time

    return render(request, "auctions.html", {
        "auctions": auctions_list,
        "unread_count": unread_count,
        "current_time": current_time
    })

def auction_request(request):
    if request.method == "POST":
        title = request.POST.get("title")
        image = request.FILES.get("image")
        reserve_price = request.POST.get("reserve_price")
        notes = request.POST.get("notes")

        errors = []
        if not title:
            errors.append("Artwork title is required.")
        if not image:
            errors.append("Artwork image is required.")
        if not reserve_price:
            errors.append("Reserve price is required.")

        if errors:
            return render(request, "auction_request.html", {
                "errors": errors,
                "title": title,
                "reserve_price": reserve_price,
                "notes": notes,
            })

        # Save the auction request
        auction_req = AuctionRequest.objects.create(
            user=request.user,
            title=title,
            image=image,
            reserve_price=reserve_price,
            notes=notes
        )

        # 🔹 Also create an Artwork automatically for this request
        Artwork.objects.create(
            user=request.user,
            title=title,
            image=image,
            description=notes,
            status="Pending",         # mark as pending until auction is approved
            price=reserve_price,
            sale_type="auction",
        )

        # Notify admin(s)
        admins = User.objects.filter(is_superuser=True)
        for admin in admins:
            Notification.objects.create(
                user=admin,
                message=f"📢 New auction request from {request.user.username}: '{auction_req.title}'"
            )
        
        # ✅ redirect after loop
        return redirect("auctions")

    # For GET requests (when opening the page)
    return render(request, "auction_request.html")

# Only allow superusers (admins)
def is_admin(user):
    return user.is_superuser

@user_passes_test(is_admin)
def admin_dashboard(request):
    users = User.objects.all()
    artworks = Artwork.objects.filter(sale_type="fixed").order_by('-id')
    auction_requests = AuctionRequest.objects.all().order_by('-created_at')

    now = timezone.now()
    active_auctions = Auction.objects.filter(start_time__lte=now, end_time__gte=now).count()
    auctions = Auction.objects.select_related('artwork').filter(
        artwork__sale_type="auction"
    ).annotate(
        is_live=Case(
            When(start_time__lte=now, end_time__gte=now, then=Value(1)),
            default=Value(0),
            output_field=IntegerField()
        )
    ).order_by('-is_live', '-start_time')
    # Attach bids to each auction
    for auction in auctions:
        bids = Bid.objects.filter(auction=auction).order_by('-amount')
        auction.bidders = bids
        if bids.exists():
            auction.highest_bid = bids.first().amount
            auction.highest_bidder = bids.first().user  # ✅ Assign User instance
        else:
            auction.highest_bid = None
            auction.highest_bidder = None

    # Weekly total live auctions
    last_7_days = [now - timedelta(days=i) for i in range(6, -1, -1)]
    weekly_counts = []
    for day in last_7_days:
        start_of_day = day.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        count = Auction.objects.filter(start_time__lte=end_of_day, end_time__gte=start_of_day).count()
        weekly_counts.append(count)

    # Notification badges
    new_users_count = User.objects.filter(is_new=True).count() if hasattr(User, 'is_new') else 0
    new_artworks_count = Artwork.objects.filter(is_new=True).count() if hasattr(Artwork, 'is_new') else 0
    new_auctions_count = Auction.objects.filter(is_new=True).count() if hasattr(Auction, 'is_new') else 0
    pending_auction_requests_count = AuctionRequest.objects.filter(status='Pending').count()

    context = {
        'users': users,
        'artworks': artworks,
        'auctions': auctions,
        'auction_requests': auction_requests,
        'active_auctions': active_auctions,
        'weekly_days': [day.strftime('%a') for day in last_7_days],
        'weekly_counts': weekly_counts,
        'new_users_count': 0 if request.session.get('seen_users') else new_users_count,
        'new_artworks_count': 0 if request.session.get('seen_artworks') else new_artworks_count,
        'new_auctions_count': 0 if request.session.get('seen_auctions') else new_auctions_count,
        'pending_auction_requests_count': 0 if request.session.get('seen_requests') else pending_auction_requests_count,
    }
    return render(request, 'artworks/admindashboard.html', context)


# ✅ Manage Users
@user_passes_test(is_admin)
def manage_users(request):
    request.session['seen_users'] = True  # mark users badge as seen
    users = User.objects.all()
    # You can either render a separate template or redirect back to dashboard
    return render(request, 'artworks/manage_users.html', {'users': users})

# ✅ Manage Auction Requests
@user_passes_test(is_admin)
def manage_auction_requests(request):
    request.session['seen_requests'] = True  # mark requests badge as seen
    auction_requests = AuctionRequest.objects.all()
    return render(request, 'artworks/manage_auction_requests.html', {'auction_requests': auction_requests})

# ✅ Manage Artworks
@user_passes_test(is_admin)
def manage_artworks(request):
    request.session['seen_artworks'] = True  # mark artworks badge as seen
    artworks = Artwork.objects.all()
    return render(request, 'artworks/manage_artworks.html', {'artworks': artworks})

# ✅ Manage Auctions
@user_passes_test(is_admin)
def manage_auctions(request):
    request.session['seen_auctions'] = True  # mark auctions badge as seen
    auctions = Auction.objects.all()
    return render(request, 'artworks/manage_auctions.html', {'auctions': auctions})




@user_passes_test(is_admin)
def approve_auction_request(request, pk):
    auction_req = get_object_or_404(AuctionRequest, pk=pk)

    
    # Step 1: Mark as in_progress
    auction_req.status = "in_progress"
    auction_req.save()

    

    # Step 2: Create corresponding Artwork for auction
    artwork = Artwork.objects.create(
        user=auction_req.user,
        title=auction_req.title,
        image=auction_req.image,
        status="Approved",
        sale_type="auction",  # 🔹 mark as auction
        price=auction_req.reserve_price
    )

    # Step 3: Create Auction
    Auction.objects.create(
        artwork=artwork,
        created_by=auction_req.user,
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(days=7),
        reserve_price=auction_req.reserve_price
    )

    # Step 4: Notify user
    Notification.objects.create(
        user=auction_req.user,
        message=f"📢 Your auction request '{auction_req.title}' has been accepted and is in progess. {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    return redirect('/admindashboard/#notifications')

@user_passes_test(is_admin)
def reject_auction_request(request, pk):
    auction_req = get_object_or_404(AuctionRequest, pk=pk)
    auction_req.status = "rejected"
    auction_req.save()

    # Send notification to user
    Notification.objects.create(
        user=auction_req.user,
        message=f"❌ Your auction request '{auction_req.title}' has been rejected.{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    return redirect('admindashboard')


@user_passes_test(lambda u: u.is_superuser)
def create_auction(request, req_id):
    auction_req = get_object_or_404(AuctionRequest, id=req_id)
    artworks = Artwork.objects.filter(user=auction_req.user)
    preselected_artwork = artworks.first() if artworks.exists() else None

    if request.method == "POST":
        artwork_id = request.POST.get("artwork_id")
        start_time_str = request.POST.get("start_time")
        end_time_str = request.POST.get("end_time")
        reserve_price = request.POST.get("reserve_price")

        if not artwork_id:
            return render(request, "artworks/create_auction.html", {
                "auction_req": auction_req,
                "artworks": artworks,
                "preselected_artwork": preselected_artwork,
                "error": "Please select an artwork."
            })

        artwork = get_object_or_404(Artwork, id=artwork_id)

         # 🔹 Make sure the selected artwork is marked as auction
        artwork.sale_type = "auction"
        artwork.save()

        start_time = timezone.make_aware(datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M"))
        end_time = timezone.make_aware(datetime.strptime(end_time_str, "%Y-%m-%dT%H:%M"))
        reserve_price = Decimal(reserve_price)

        Auction.objects.create(
            artwork=artwork,
            created_by=request.user,
            start_time=start_time,
            end_time=end_time,
            reserve_price=reserve_price,
            auction_request=auction_req
        )

        auction_req.status = "approved"
        auction_req.save()

        Notification.objects.create(
            user=auction_req.user,
            message=f"✅ Your artwork '{artwork.title}' has been approved for live auction! {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Notify all users about live auction
        
        all_users = User.objects.exclude(is_superuser=True)
        for u in all_users:
            message = format_html(
                "🎨 A new auction for '{}' is now live! <a href='{}'>Join and place your bids!</a>",
                artwork.title,
                reverse('auctions')
            )
            Notification.objects.create(user=u, message=message)

        messages.success(request, "Auction created and users notified!")
        return redirect('/admindashboard/#auctions')

    return render(request, "artworks/create_auction.html", {
        "auction_req": auction_req,
        "artworks": artworks,
        "preselected_artwork": preselected_artwork
    })


@user_passes_test(is_admin)
def send_auction(request, req_id):
    auction_req = get_object_or_404(AuctionRequest, id=req_id)
    auction = Auction.objects.filter(auction_request=auction_req).first()

    if auction and auction_req.status == "approved":
        auction_req.status = "sent"
        auction_req.save()

        Notification.objects.create(
            user=auction.created_by,
           
        )

        return redirect('admindashboard')


@staff_member_required
def start_auction(request, auction_id):
    auction = get_object_or_404(Auction, id=auction_id)
    # Set start time to now
    auction.start_time = timezone.now()
    auction.save()

    return redirect('admindashboard')


@user_passes_test(is_admin)
def edit_auction(request, pk):
    auction = get_object_or_404(Auction, pk=pk)

    if request.method == "POST":
        form = AuctionForm(request.POST, instance=auction)
        if form.is_valid():
            form.save()
            return redirect('/admindashboard/#auctions')
    else:
        form = AuctionForm(instance=auction)

        # Pre-fill datetime-local fields with the correct format
        if auction.start_time:
            form.fields['start_time'].initial = auction.start_time.strftime("%Y-%m-%dT%H:%M")
        if auction.end_time:
            form.fields['end_time'].initial = auction.end_time.strftime("%Y-%m-%dT%H:%M")

    return render(request, "artworks/edit_auction.html", {
        "auction": auction,
        "form": form
    })

@staff_member_required
def delete_auction(request, pk):
    auction = get_object_or_404(Auction, pk=pk)
    title = auction.artwork.title
    auction.delete()
    return redirect('/admindashboard/#auctions')


@login_required
@csrf_exempt  # Required for AJAX POST if CSRF token not working
def place_bid_ajax(request, auction_id):
     if request.method == "POST":
        try:
            data = json.loads(request.body)
            bid_amount = int(data.get("bid_amount", 0))
        except (ValueError, json.JSONDecodeError):
            return JsonResponse({"success": False, "message": "Invalid bid data."})

        auction = get_object_or_404(Auction, id=auction_id)

        # Get current highest bid
        highest_bid = Bid.objects.filter(auction=auction).order_by("-amount").first()
        min_bid = highest_bid.amount if highest_bid else auction.reserve_price

        if bid_amount <= min_bid:
            return JsonResponse({
                "success": False,
                "message": f"Bid must be greater than ₹{min_bid}."
            })

        # Create new bid
        bid = Bid.objects.create(
            auction=auction,
            user=request.user,
            amount=bid_amount
        )

        # Update auction’s highest bidder + highest bid
        auction.highest_bid = bid.amount
        auction.highest_bidder = bid.user
        auction.save()

        return JsonResponse({
            "success": True,
            "message": f"Your bid of ₹{bid_amount} has been placed!",
            "new_highest_bid": bid.amount,
            "highest_bidder": bid.user.username  # ✅ send username
        })

     return JsonResponse({"success": False, "message": "Invalid request."})


@user_passes_test(is_admin)
def approve_artwork(request, artwork_id, sale_type):
    art = get_object_or_404(Artwork, id=artwork_id)
    art.status = 'approved'
    art.sale_type = sale_type  # 'fixed' or 'auction'
    art.save()
    messages.success(request, f"{art.title} approved for {sale_type} sale.")
    return redirect('admindashboard')


def get_current_winners(request):
    # Get auctions that have ended and the winner has been announced
    auctions = Auction.objects.filter(winner_announced=True).order_by('-end_time')

    data = [
        {
            "auction_id": auction.id,
            "artwork_title": auction.artwork.title,
            "winner": auction.winner.username if auction.winner else None,
            "price": float(auction.highest_bid)
        }
        for auction in auctions
    ]
    return JsonResponse(data, safe=False)



@login_required
@require_POST
def announce_winner_ajax(request, auction_id):
    auction = get_object_or_404(Auction, id=auction_id)
    if auction.is_ended() and not auction.winner_announced:
        if auction.highest_bidder:  # ensure there is a highest bidder
            auction.winner = auction.highest_bidder
            auction.winner_announced = True
            auction.save()

            winner_link = reverse('payment_page', args=[auction.id])

            # Correct format_html usage
            message = format_html(
                "🎉 Congratulations! You won the auction '{}'! <a href='{}'>Go to Auction & Pay</a>",
                auction.artwork.title,
                winner_link
            )

            Notification.objects.create(user=auction.winner, message=message)

             # 🔹 Notify original artwork owner
            owner_link = reverse('userdashboard')  # or link to auction details if you have one
            owner_message = format_html(
                "✅ Your artwork '{}' has been sold! Winner: {}. <a href='{}'>Go to Dashboard</a>",
                auction.artwork.title,
                auction.winner.username,
                owner_link
            )
            Notification.objects.create(user=auction.artwork.user, message=owner_message)

            return JsonResponse({
                'success': True,
                'message': f"Winner announced: {auction.winner.username}",
                'winner': auction.winner.username
            })
        else:
            return JsonResponse({'success': False, 'message': 'No bids placed yet'})
    return JsonResponse({'success': False, 'message': 'Auction not ended or winner already announced'})



def delete_artwork(request, art_id):
    if not request.user.is_staff:
      
      return redirect('/')  # fallback

    artwork = get_object_or_404(Artwork, id=art_id)
    artwork.delete()
   
    return redirect('/admindashboard/#artworks')  # ensure URL name exists


def profile(request):
    user = request.user

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        bio = request.POST.get("bio", "").strip()
        profile_image = request.FILES.get("profile_image")

        if full_name:
            parts = full_name.split(" ", 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ""
        if email:
            user.email = email
        if bio:
            user.bio = bio
        if profile_image:
            user.profile_image = profile_image

        user.save()
        return redirect('profile_view', username=user.username)

    return render(request, "artworks/profile.html", {"user": user})


@login_required
def profile_edit(request):
    """Edit current user's profile. After save redirect to profile_view (username)."""
    user = request.user
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile_view', username=user.username)
    else:
        form = ProfileForm(instance=user)
    return render(request, 'artworks/profile.html', {'form': form})




def profile_view(request, username):
    profile_user = get_object_or_404(User, username=username)
    artworks = Artwork.objects.filter(user=profile_user, sale_type='fixed', status='pending')
    is_owner = request.user == profile_user
    return render(request, 'artworks/profile_view.html', {
        'profile_user': profile_user,
        'artworks': artworks,
        'is_owner': is_owner,
    })


@login_required
def profile_add_artwork(request):
    """Add fixed-price artwork from logged-in user's profile — auto publish (Approved)."""
    if request.method == 'POST':
        form = FixedArtworkForm(request.POST, request.FILES)
        if form.is_valid():
            art = form.save(commit=False)
            art.user = request.user
            art.sale_type = 'fixed'
            art.status = 'Approved'   # Auto-publish
            art.save()
            messages.success(request, "Artwork uploaded and published.")
            return redirect('profile_view', username=request.user.username)
    else:
        form = FixedArtworkForm()
    return render(request, 'artworks/profile_add_artwork.html', {'form': form})


@login_required
def profile_redirect(request):
    user = request.user
    if user.first_name or user.bio or user.profile_image:
        return redirect('profile_view', username=user.username)
    return redirect('profile_form')



@login_required
@csrf_exempt
def fixed_payment(request, art_id):
    art = get_object_or_404(Artwork, id=art_id)
    
    # Process payment logic here
    payment_success = True  # Replace with real payment check

    if payment_success:
        art.sold = True
        art.status = "SOLD"
        art.save()
        return redirect('fixed_sales')  # Redirect to fixed sales page
    else:
        return redirect('fixed_sales')







@login_required
def cart_page(request):
    unread_count = request.user.notifications.filter(is_read=False).count()  # if using notification system
    return render(request, "artworks/cart.html", {"unread_count": unread_count})





        

@login_required
def add_to_cart(request, artwork_id):
    if request.method == "POST":
        user = request.user
        try:
            artwork = Artwork.objects.get(id=artwork_id, sold=False)
            # Check if already in cart
            if CartItem.objects.filter(user=user, artwork=artwork).exists():
                return JsonResponse({'success': False, 'message': 'Already in cart'})
            CartItem.objects.create(user=user, artwork=artwork, price=artwork.price)
            return JsonResponse({'success': True, 'message': 'Added to cart'})
        except Artwork.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Artwork not available'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required
def start_payment_session(request, art_id):
    try:
        artwork = Artwork.objects.get(id=art_id, sold=False)

        # Create payment session ONLY if not already created
        session, created = PaymentSession.objects.get_or_create(
            user=request.user,
            artwork=artwork,
            status="PENDING"
        )

        return JsonResponse({
            'success': True,
            'message': 'Payment session started',
            'redirect_url': f'/payment/checkout/{session.id}/'
        })

    except Artwork.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Artwork unavailable'})
    

# def payment_page(request, session_id):
#     payment_session = get_object_or_404(PaymentSession, id=session_id)

#     if request.method == "POST":
#         # Simulate successful payment
#         payment_session.status = 'PAID'
#         payment_session.save()

#         # Update artwork sold status
#         artwork = payment_session.artwork
#         artwork.sold = True
#         artwork.save()

#         messages.success(request, f"Payment Successful! You bought '{artwork.title}'.")
#         return redirect('fixed_sales')

#     return render(request, 'payment.html', {'session': payment_session})




@login_required
def confirm_payment(request, session_id):
    session = get_object_or_404(PaymentSession, id=session_id, user=request.user, status="PENDING")
    artwork = session.artwork

    # Mark as sold
    artwork.sold = True
    artwork.save()

    # Mark payment session as completed
    session.status = "PAID"
    session.save()

    return redirect('fixed_sales')


@csrf_exempt
def fixed_cart_payment(request):
    if request.method == "POST" and request.user.is_authenticated:
        try:
            data = json.loads(request.body)
            artwork_ids = data.get("artworks", [])

            if not artwork_ids:
                return JsonResponse({"success": False, "message": "No artworks selected."})

            updated_artworks = []
            for art_id in artwork_ids:
                try:
                    art = Artwork.objects.get(id=art_id, sold=False)
                    art.sold = True
                    art.status = "SOLD"
                    art.save()
                    updated_artworks.append(art.title)
                except Artwork.DoesNotExist:
                    continue

            if not updated_artworks:
                return JsonResponse({"success": False, "message": "Artworks already sold or invalid."})

            return JsonResponse({
                "success": True,
                "message": f"Payment successful for: {', '.join(updated_artworks)}"
            })

        except Exception as e:
            return JsonResponse({"success": False, "message": f"Error: {str(e)}"})

    return JsonResponse({"success": False, "message": "Invalid request or not authenticated."})


@login_required
@csrf_exempt
def initiate_payment(request, art_id):
    artwork = get_object_or_404(Artwork, id=art_id)

    if artwork.sold:
        messages.error(request, "This artwork is already sold.")
        return redirect('fixed_sales')

    # Create payment session
    payment_session = PaymentSession.objects.create(
        user=request.user,
        artwork=artwork,
        amount=artwork.price
    )
    return redirect('artworks/payment.html', session_id=payment_session.id)



@login_required
def get_payment_session(request, session_id):
    session = get_object_or_404(PaymentSession, id=session_id, user=request.user)
    return JsonResponse({
        'success': True,
        'artwork': {
            'title': session.artwork.title,
            'image': session.artwork.image.url,
            'price': float(session.amount)
        }
    })


@login_required
@csrf_exempt
def finalize_payment(request):
    if request.method == "POST":
        import json
        data = json.loads(request.body)
        artwork_id = data.get('session_id')
        user = request.user

        try:
            artwork = Artwork.objects.get(id=artwork_id)

            if artwork.sold:
                return JsonResponse({'success': False, 'message': 'Artwork already sold.'})

            # Create payment session
            payment = PaymentSession.objects.create(
                user=user,
                artwork=artwork,
                amount=artwork.price,
                status="PAID"  # ✅ Mark as paid
            )

            # Update artwork sold status
            artwork.sold = True
            artwork.save()

            return JsonResponse({'success': True, 'message': 'Payment successful.'})

        except Artwork.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Artwork not found.'})
    return JsonResponse({'success': False, 'message': 'Invalid request.'})

@login_required
@csrf_exempt
def fixed_cart_payment(request):
    if request.method == "POST":
        data = json.loads(request.body)
        artwork_ids = data.get("artworks", [])

        for art_id in artwork_ids:
            try:
                artwork = Artwork.objects.get(id=art_id, sold=False)
                artwork.sold = True
                artwork.status = "SOLD"
                artwork.save()
                # Remove from cart
                CartItem.objects.filter(user=request.user, artwork=artwork).delete()
            except Artwork.DoesNotExist:
                continue

        return JsonResponse({"success": True, "message": "Payment completed"})
    

@login_required
def payment_success(request):
    session_id = request.GET.get("session_id")
    if not session_id:
        return redirect('fixed_sales')

    try:
        session = PaymentSession.objects.get(id=session_id, user=request.user)
        artwork = session.artwork

        # Finalize artwork
        artwork.sold = True
        artwork.status = "SOLD"
        artwork.save()

        # Mark session as paid
        if hasattr(session, 'paid'):
            session.paid = True
        else:
            session.status = "PAID"
        session.save()

        # Remove from cart
        CartItem.objects.filter(user=request.user, artwork=artwork).delete()

        # Redirect to fixed_sales with sold_artwork parameter
        return redirect(f"{reverse('fixed_sales')}?sold_artwork={artwork.id}")

    except PaymentSession.DoesNotExist:
        return redirect('fixed_sales')
