# Generated by Django 5.1.2 on 2024-11-18 03:42

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('naturalworld_d', '0021_alter_cliente_options_remove_pedido_productos_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedido',
            name='productos',
            field=models.ManyToManyField(related_name='pedidos', through='naturalworld_d.PedidoProducto', to='naturalworld_d.producto'),
        ),
        migrations.AddField(
            model_name='pedido',
            name='rut',
            field=models.CharField(blank=True, max_length=12, null=True),
        ),
        migrations.AlterField(
            model_name='pedido',
            name='cliente',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='naturalworld_d.cliente'),
        ),
    ]