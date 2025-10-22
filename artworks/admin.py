from django.contrib import admin
from django.utils import timezone
from django.urls import path
from django.template.response import TemplateResponse
import json

from .models import User, Artwork, AuctionRequest, Auction, Bid


# Register your models here.

class AuctionRequestAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "user__username")
    actions = ["approve_request", "reject_request", "mark_in_progress"]

    def approve_request(self, request, queryset):
        for req in queryset:
            if not Auction.objects.filter(auction_request=req).exists():
                # Create auction from request
                Auction.objects.create(
                    artwork=Artwork.objects.get(id=req.id),  # Adjust this if artwork is separate
                    auction_request=req,
                    start_time=timezone.now(),
                    end_time=timezone.now() + timezone.timedelta(days=3),
                    reserve_price=req.reserve_price,
                    created_by=req.user,
                )
            req.status = "approved"
            req.save()
    approve_request.short_description = "Approve selected requests"

    def reject_request(self, request, queryset):
        queryset.update(status="rejected")
    reject_request.short_description = "Reject selected requests"

    def mark_in_progress(self, request, queryset):
        queryset.update(status="in_progress")
    mark_in_progress.short_description = "Mark selected requests as In Progress"


# ───── Bid Inline for Auctions ─────
class BidInline(admin.TabularInline):
    model = Bid
    extra = 0
    readonly_fields = ("user", "amount", "created_at")
    can_delete = False


# ───── Auction Admin ─────
@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ("artwork", "auction_request", "start_time", "end_time", "reserve_price", "created_by", "get_winner")
    list_filter = ("start_time", "end_time")
    search_fields = ("artwork__title", "created_by__username")
    inlines = [BidInline]
    change_list_template = "admin/auction_change_list.html"  # optional custom template

    actions = ["pause_auctions", "resume_auctions", "stop_auctions"]

    # Custom admin actions
    def pause_auctions(self, request, queryset):
        queryset.update(end_time=timezone.now())
    pause_auctions.short_description = "Pause selected auctions (set end_time now)"

    def resume_auctions(self, request, queryset):
        for auction in queryset:
            auction.end_time += timezone.timedelta(days=1)
            auction.save()
    resume_auctions.short_description = "Resume selected auctions (extend end_time)"

    def stop_auctions(self, request, queryset):
        queryset.update(end_time=timezone.now())
    stop_auctions.short_description = "Stop selected auctions"

    # Show auction winner (highest bid)
    def get_winner(self, obj):
        highest_bid = obj.bids.first()  # bids ordered descending
        if highest_bid:
            return f"{highest_bid.user.username} ({highest_bid.amount})"
        return "-"
    get_winner.short_description = "Winner"

    # Custom URL for monitoring bids
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:auction_id>/monitor/', self.admin_site.admin_view(self.monitor_bids), name='auction-monitor'),
        ]
        return custom_urls + urls

    # View for monitoring bids with chart
    def monitor_bids(self, request, auction_id):
        auction = Auction.objects.get(id=auction_id)
        bids = auction.bids.all()
        bid_data = [
            {"user": b.user.username, "amount": float(b.amount), "time": b.created_at.strftime("%Y-%m-%d %H:%M:%S")}
            for b in bids
        ]
        context = dict(
            self.admin_site.each_context(request),
            auction=auction,
            bids=bids,
            bid_data=json.dumps(bid_data)  # for Chart.js
        )
        return TemplateResponse(request, "admin/auction_monitor.html", context)


# ───── Register Artwork & User for completeness ─────
@admin.register(Artwork)
class ArtworkAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "price", "status")
    search_fields = ("title", "user__username")
    list_filter = ("status",)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "is_artist", "is_buyer")
    search_fields = ("username",)