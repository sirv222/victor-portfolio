from django import forms


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=300,
        min_length=2,
        strip=True,
        widget=forms.TextInput(attrs={'placeholder': 'Jane Doe', 'required': True}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'jane@example.com', 'required': True}),
    )
    subject = forms.CharField(
        max_length=300,
        min_length=3,
        strip=True,
        widget=forms.TextInput(attrs={'placeholder': 'Project inquiry', 'required': True}),
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 6, 'placeholder': 'Tell me about your project...', 'required': True}),
        min_length=10,
        strip=True,
    )