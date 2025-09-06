from rest_framework import serializers
from accounts.models import User
from core.utils import send_verification_email


class UserSerializer(serializers.ModelSerializer):
    profile_image = serializers.ImageField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'is_employer', 'is_seeker',
            'phone', 'company_name', 'company_website', 'skills', 'experience', 'profile_image'
        ]
        read_only_fields = ['id', 'is_employer', 'is_seeker', 'profile_image']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=(('seeker', 'Seeker'), ('employer', 'Employer')))

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'role']

    def create(self, validated_data):
        role = validated_data.pop('role')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        if role == 'seeker':
            user.is_seeker = True
        else:
            user.is_employer = True
        # New users must verify email
        user.email_verified = False
        user.save()

        # Send verification email (keeps behavior consistent with web registration)
        try:
            send_verification_email(user)
        except Exception:
            # Don't fail registration if email sending fails; client can request resend later
            pass

        return user
