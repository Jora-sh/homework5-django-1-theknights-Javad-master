from social_core.pipeline.partial import partial
from django.shortcuts import redirect
from django.urls import reverse

@partial
def set_user_role(strategy, details, backend, user=None, is_new=False, *args, **kwargs):
    # Skip if we already have a user with a role
    if user and (user.is_seeker or user.is_employer):
        return

    # Get the role from session
    role = strategy.session_get('social_auth_role')

    if not role:
        # Store current partial pipeline data in session
        current_partial = kwargs.get('current_partial')
        strategy.session_set('partial_pipeline_token', current_partial.token)
        strategy.session_set('partial_pipeline_backend', backend.name)
        # Redirect to role selection page
        return redirect(reverse('accounts:social_auth_role_selection'))

    # We have a role, let's set it
    if user:
        # Set the role for existing user
        if role == 'seeker':
            user.is_seeker = True
        else:
            user.is_employer = True
        user.email_verified = True  # Since we got this from Google, we can trust the email
        user.save()
    else:
        # For new user creation, update the details
        details['is_seeker'] = role == 'seeker'
        details['is_employer'] = role == 'employer'
        details['email_verified'] = True

    # Remove the role from session after using it
    strategy.session_set('social_auth_role', None)
    return
