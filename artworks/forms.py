from django import forms
from .models import Auction, User, Artwork


class AuctionForm(forms.ModelForm):
    class Meta:
        model = Auction
        fields = ['start_time', 'end_time', 'reserve_price']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'bio', 'location', 'profile_image']

class FixedArtworkForm(forms.ModelForm):
    class Meta:
        model = Artwork
        fields = ['title', 'description', 'image', 'price']
        widgets = {
            'description': forms.Textarea(attrs={'rows':3}),
        }