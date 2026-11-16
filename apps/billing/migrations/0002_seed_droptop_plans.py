from django.db import migrations


GIB = 1024**3

PLANS = [
    {
        "slug": "free",
        "name": "Free",
        "amount_minor": 0,
        "storage_limit_bytes": 5 * GIB,
        "display_order": 0,
        "features": [
            "5 GB photo storage",
            "Unlimited galleries",
            "Client favorites",
            "Secure gallery sharing",
        ],
    },
    {
        "slug": "basic",
        "name": "Basic",
        "amount_minor": 500,
        "storage_limit_bytes": 10 * GIB,
        "display_order": 1,
        "features": [
            "All Free features",
            "30 minutes of HD video",
            "Custom branding",
            "Connect a custom domain",
            "Full-resolution downloads",
            "100 campaign emails per month",
            "Unlimited mobile gallery apps",
            "Commission-free sales",
        ],
    },
    {
        "slug": "plus",
        "name": "Plus",
        "amount_minor": 1200,
        "storage_limit_bytes": 100 * GIB,
        "display_order": 2,
        "features": [
            "All Basic features",
            "1 hour of HD video",
            "500 campaign emails per month",
        ],
    },
    {
        "slug": "pro",
        "name": "Pro",
        "amount_minor": 2000,
        "storage_limit_bytes": 1000 * GIB,
        "display_order": 3,
        "features": [
            "All Plus features",
            "2 hours of 4K video",
            "5,000 campaign emails per month",
            "Bulk share collections",
            "RAW photo support",
        ],
    },
]


def seed_plans(apps, schema_editor):
    BillingPlan = apps.get_model("billing", "BillingPlan")
    for plan in PLANS:
        BillingPlan.objects.update_or_create(
            slug=plan["slug"],
            defaults={
                **plan,
                "currency": "USD",
                "interval": "monthly",
                "is_active": True,
            },
        )


def remove_plans(apps, schema_editor):
    BillingPlan = apps.get_model("billing", "BillingPlan")
    BillingPlan.objects.filter(slug__in=[plan["slug"] for plan in PLANS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0001_initial"),
        ("quotas", "0002_alter_storagequota_plan_name_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_plans, remove_plans),
    ]
