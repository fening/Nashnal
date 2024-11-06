from django.urls import path
from .views import register_view, login_view, logout_view,profile_view,employee_list_view, complete_registration, CustomPasswordResetView, CustomPasswordResetDoneView,CustomPasswordResetConfirmView, CustomPasswordResetCompleteView
from . import views

urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),
    path('employees/', employee_list_view, name='employee_list'),
    path('employees/create/', views.employee_create, name='employee_create'),
    path('employees/<int:pk>/update/', views.employee_update, name='employee_update'),
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),
        # Registration completion
    path('complete-registration/<uuid:token>/', complete_registration, name='complete_registration'),
    path('invitations/', views.manage_invitations, name='manage_invitations'),
    path('resend-invitation/<int:invitation_id>/', views.resend_invitation, name='resend_invitation'),
    path('cancel-invitation/<int:invitation_id>/', views.cancel_invitation, name='cancel_invitation'),
    
    path('password-reset/', 
         CustomPasswordResetView.as_view(), 
         name='password_reset'),
    path('password-reset/done/', 
         CustomPasswordResetDoneView.as_view(), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         CustomPasswordResetConfirmView.as_view(), 
         name='password_reset_confirm'),
    path('password-reset-complete/',
         CustomPasswordResetCompleteView.as_view(), 
         name='password_reset_complete'),
]