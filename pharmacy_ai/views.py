from django.shortcuts import redirect, render


def landing_entry_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "public/landing.html")
