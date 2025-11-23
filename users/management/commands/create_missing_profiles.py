from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Profile

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates Profile objects for all existing users who do not have one'

    def handle(self, *args, **options):
        users_without_profile = []
        users_with_profile = 0
        
        for user in User.objects.all():
            if not hasattr(user, 'profile'):
                users_without_profile.append(user)
            else:
                users_with_profile += 1
        
        if not users_without_profile:
            self.stdout.write(
                self.style.SUCCESS(
                    f'All {users_with_profile} users already have profiles. Nothing to do.'
                )
            )
            return
        
        # Create profiles for users without one
        profiles_created = 0
        for user in users_without_profile:
            Profile.objects.create(user=user)
            profiles_created += 1
            self.stdout.write(
                self.style.SUCCESS(f'Created profile for user: {user.username}')
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary:\n'
                f'  - Profiles created: {profiles_created}\n'
                f'  - Existing profiles: {users_with_profile}\n'
                f'  - Total users: {profiles_created + users_with_profile}'
            )
        )
