from .models import (
    About,
    Contact,
    Education,
    Experience,
    FAQ,
    PersonalDetails,
    Projects,
    Skill,
    Technology,
    Value,
)


def portfolio_data(request):
    """Provide shared portfolio data to templates across the project."""
    engineer = PersonalDetails.objects.first()
    contact = Contact.objects.prefetch_related('socials').first()
    tech_stack = Technology.objects.all().order_by('name')
    skills = Skill.objects.prefetch_related('skill_stack').all()
    projects = Projects.objects.prefetch_related('project_stack', 'project_category').all()
    about = About.objects.first()
    faqs = FAQ.objects.all()
    recent_projects = projects.order_by('-date')[:3]
    experience = Experience.objects.all().order_by('-date', '-start_date')
    education = Education.objects.all().order_by('-date', '-start_date')
    values = Value.objects.all()
    oss_projects_count = projects.filter(project_category__choice='oss').distinct().count()

    if engineer is not None:
        engineer.contributions = oss_projects_count
        engineer.save(update_fields=['contributions'])

    return {
        'engineer': engineer,
        'contact': contact,
        'tech_stack': tech_stack,
        'skill': skills,
        'project': projects,
        'about': about,
        'question': faqs,
        'no_of_project': projects.count(),
        'no_of_oss_projects': oss_projects_count,
        'recent_project': recent_projects,
        'experience': experience,
        'education': education,
        'value': values,
    }