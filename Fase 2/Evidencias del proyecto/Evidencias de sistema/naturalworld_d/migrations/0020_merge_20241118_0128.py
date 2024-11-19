from django.db import migrations

def populate_email(apps, schema_editor):
    Cliente = apps.get_model('naturalworld_d', 'Cliente')
    for cliente in Cliente.objects.filter(email__isnull=True):
        cliente.email = f"default_{cliente.id}@example.com"
        cliente.save()

class Migration(migrations.Migration):

    dependencies = [
        ('naturalworld_d', '0018_cliente_user_alter_cliente_email'),
        ('naturalworld_d', '0019_populate_email'),
    ]

    operations = [
        migrations.RunPython(populate_email),
    ]
