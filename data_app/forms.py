from django import forms

class UploadFileForm(forms.Form):
    file = forms.FileField()
class DataForm(forms.Form):
    name = forms.CharField(max_length=100, required=True)
    description = forms.CharField(widget=forms.Textarea, required=False)
    file = forms.FileField(required=False)

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file and not file.name.endswith('.csv'):
            raise forms.ValidationError("Only CSV files are allowed.")
        return file