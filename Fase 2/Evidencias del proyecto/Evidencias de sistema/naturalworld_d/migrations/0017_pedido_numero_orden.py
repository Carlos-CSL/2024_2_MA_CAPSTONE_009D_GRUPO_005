from django.db import migrations, models

def set_unique_order_numbers(apps, schema_editor):
    Pedido = apps.get_model('naturalworld_d', 'Pedido')
    for index, pedido in enumerate(Pedido.objects.all(), start=1):
        pedido.numero_orden = f"ORD-{index:04d}"
        pedido.save()

class Migration(migrations.Migration):

    dependencies = [
        ('naturalworld_d', '0016_alter_pedidoproducto_pedido'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedido',
            name='numero_orden',
            field=models.CharField(max_length=20, unique=True, blank=True, null=True),
        ),
        migrations.RunPython(set_unique_order_numbers),
        migrations.AlterField(
            model_name='pedido',
            name='numero_orden',
            field=models.CharField(max_length=20, unique=True, blank=True),
        ),
    ]
