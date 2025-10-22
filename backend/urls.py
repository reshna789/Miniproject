from django.contrib import admin
from django.urls import path, include
from artworks import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Artwork app routes
    path("", include("artworks.urls")),  # Keeps all routes from artworks/urls.py

    # User authentication
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('logout-page/', views.logout_page, name='logout_page'),
    path('forgot/', views.forgot_password, name='forgot'), 

    # Dashboards
    path('userdashboard/', views.user_dashboard, name='userdashboard'),
    path('admindashboard/', views.admin_dashboard, name='admindashboard'),

    # Artworks
    path('upload/', views.upload_artwork, name='upload'),
    path('fps-uploadform/', views.fps_uploadform, name='fps_uploadform'),
    path('fixed-sales/', views.fixed_sales, name='fixed_sales'),
    path('manage-artworks/', views.manage_artworks, name='manage_artworks'),
    path('delete-artwork/<int:art_id>/', views.delete_artwork, name='delete_artwork'),

    # Auctions
    path('auctions/', views.auctions, name='auctions'),
    path('auction-request/', views.auction_request, name='auction_request'),
    path('auction-request/<int:pk>/approve/', views.approve_auction_request, name='approve_auction_request'),
    path('auction-request/<int:pk>/reject/', views.reject_auction_request, name='reject_auction_request'),
    path('admindashboard/create-auction/<int:req_id>/', views.create_auction, name='create_auction'),
    path('admindashboard/send-auction/<int:req_id>/', views.send_auction, name='send_auction'),
    path('auction/<int:auction_id>/place_bid_ajax/', views.place_bid_ajax, name='place_bid_ajax'),
    path('auction/<int:pk>/edit/', views.edit_auction, name='edit_auction'),
    path('auction/<int:pk>/delete/', views.delete_auction, name='delete_auction'),
    path('auction/<int:pk>/start/', views.start_auction, name='start_auction'),
    path('manage-auctions/', views.manage_auctions, name='manage_auctions'),
    path('manage-auction-requests/', views.manage_auction_requests, name='manage_auction_requests'),
    path('announce-winner/<int:auction_id>/', views.announce_winner_ajax, name='announce_winner_ajax'),
    path('api/winners/', views.get_current_winners, name='get_current_winners'),

    # Cart
    path('cart/', views.cart_view, name='cart'),
    # path('cart/get/', views.get_cart_items, name='get_cart_items'),
    # path('cart/remove/<int:art_id>/', views.remove_cart_item, name='remove_cart_item'),
    # path('cart/add/<int:artwork_id>/', views.add_to_cart, name='add_to_cart'),


    # Payment
    # path('payment/back/', views.payment_back, name='payment_back'),
    # # path('payment/<int:auction_id>/', views.payment_page, name='payment_page'),
    # path('payment/fixed/<int:artwork_id>/', views.start_payment_session, name='start_payment_session'),
    # # path('payment/fixed/checkout/', views.fixed_payment_checkout, name='payment_fixed_checkout'),
    # # path('payment/checkout/<int:session_id>/', views.payment_checkout, name='payment_checkout'),
    # path('payment/fixed/', views.fixed_cart_payment, name='fixed_cart_payment'),
    # path('payment/initiate/<int:artwork_id>/', views.initiate_payment, name='initiate_payment'),
    # path('payment/fixed/<int:artwork_id>/', views.fixed_payment, name='fixed_payment'),
    # path('payment/get-session/<int:session_id>/', views.get_payment_session, name='get_payment_session'),
    # path('payment/finalize/', views.finalize_payment, name='finalize_payment'),
    # path('payment/success/', views.payment_success, name='payment_success'),


    
    path('fixed_sales/', views.fixed_sales, name='fixed_sales'),
    path('payment/<int:artwork_id>/', views.payment_page, name='payment_page'),



    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),

    # Profile
    path('profile/', views.profile_redirect, name='profile_redirect'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/add-artwork/', views.profile_add_artwork, name='profile_add_artwork'),
    path('profile_form/', views.profile, name='profile_form'), 
    path('profile/<str:username>/', views.profile_view, name='profile_view'),

    # User management
    path('manage-users/', views.manage_users, name='manage_users'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
