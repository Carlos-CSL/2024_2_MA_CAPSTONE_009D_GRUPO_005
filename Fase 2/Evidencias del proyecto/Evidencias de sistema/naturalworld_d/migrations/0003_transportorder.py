# Generated by Django 5.1.1 on 2024-11-24 05:15

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('naturalworld_d', '0002_alter_pedido_marketplace_rut_alter_pedido_seller_rut'),
    ]

    operations = [
        migrations.CreateModel(
            name='TransportOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transport_order_number', models.CharField(help_text='Número de la Orden de Transporte generado por Chilexpress', max_length=20, unique=True)),
                ('certificate_number', models.BigIntegerField(blank=True, help_text='Número del certificado asociado a la orden de transporte', null=True)),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente'), ('generado', 'Generado'), ('en_transito', 'En Tránsito'), ('entregado', 'Entregado')], default='pendiente', help_text='Estado actual de la orden de transporte', max_length=20)),
                ('etiqueta', models.FileField(blank=True, help_text='Etiqueta generada por Chilexpress para el envío', null=True, upload_to='etiquetas/')),
                ('respuesta_api', models.JSONField(blank=True, help_text='Respuesta completa de la API al generar la orden de transporte', null=True)),
                ('fecha_generacion', models.DateTimeField(auto_now_add=True, help_text='Fecha en que se generó la orden')),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True, help_text='Última vez que se actualizó la información')),
                ('pedido', models.OneToOneField(help_text='Pedido asociado a esta orden de transporte', on_delete=django.db.models.deletion.CASCADE, related_name='transport_order', to='naturalworld_d.pedido')),
            ],
        ),
    ]
