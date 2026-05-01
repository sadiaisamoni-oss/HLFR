"""Forms for the foodapp"""

from django import forms
from .models import Donation


class DonationForm(forms.ModelForm):
    """Form for creating and editing donations"""

    class Meta:
        model = Donation
        fields = ['food_name', 'category', 'quantity', 'location', 'donor_name']
        widgets = {
            'food_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter food item name',
                'required': True
            }),
            'category': forms.Select(attrs={
                'class': 'form-control',
            }),
            'quantity': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 5 kg, 10 items, 2 boxes',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Pickup location',
            }),
            'donor_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your name (optional)',
            }),
            # Image field removed per user request (optional)
        }


class DonationSearchForm(forms.Form):
    """Form for searching donations"""
    search_query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by food name, location, or donor...',
        })
    )
    category = forms.ChoiceField(
        required=False,
        choices=[('', 'All Categories')] + list(Donation.CATEGORY_CHOICES),
        widget=forms.Select(attrs={
            'class': 'form-control',
        })
    )
