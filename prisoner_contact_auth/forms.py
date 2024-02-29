# forms.py

from django import forms
from prison_market.models import PrisonerContact, User


class PrisonerContactForm(forms.ModelForm):
    # Include fields from the User model if needed
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = PrisonerContact
        fields = ['username', 'password', 'full_name', 'relationship', 'phone_number',
                  'email', 'address', 'additional_info', 'picture', 'prisoner']

    def save(self, commit=True):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password']
        )
        prisoner_contact = super().save(commit=False)
        prisoner_contact.user = user
        if commit:
            prisoner_contact.save()
        return prisoner_contact
