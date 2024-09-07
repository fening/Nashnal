from django.forms import modelformset_factory
from .models import Job
from .forms import JobForm

# Define the formset
JobFormSet = modelformset_factory(
    Job,
    form=JobForm,
    extra=1,  # Number of empty job forms to display initially
)
