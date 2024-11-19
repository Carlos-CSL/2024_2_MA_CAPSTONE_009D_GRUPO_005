from django.db import migrations

def populate_email(apps, schema_editor):
    Cliente = apps.get_model('naturalworld_d', 'Cliente')  # Cambia 'naturalworld_d' si tu aplicación tiene otro nombre
    for cliente in Cliente.objects.filter(email__isnull=True):
        cliente.email = f"default_{cliente.id}@example.com"  # Crea un email único para cada cliente
        cliente.save()

class Migration(migrations.Migration):
    dependencies = [
        ('naturalworld_d', '0001_initial'),  # Asegúrate de que esta sea la migración inicial correcta
    ]

    operations = [
        migrations.RunPython(populate_email),
    ]
