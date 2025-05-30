"""
Initial migration for the market app.
"""
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    """Initial migration for market app models."""
    
    initial = True
    
    dependencies = []
    
    operations = [
        migrations.CreateModel(
            name='DataSource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('base_url', models.URLField(max_length=200)),
                ('api_key_required', models.BooleanField(default=False)),
                ('rate_limit_per_minute', models.PositiveIntegerField(blank=True, help_text='Maximum number of API calls allowed per minute', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Data Source',
                'verbose_name_plural': 'Data Sources',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='CommodityCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Commodity Category',
                'verbose_name_plural': 'Commodity Categories',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Commodity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('symbol', models.CharField(max_length=20, unique=True)),
                ('exchange', models.CharField(max_length=100)),
                ('unit', models.CharField(max_length=20)),
                ('currency', models.CharField(max_length=3)),
                ('is_active', models.BooleanField(default=True)),
                ('last_updated', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='commodities', to='market.commoditycategory')),
                ('data_source', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='commodities', to='market.datasource')),
            ],
            options={
                'verbose_name': 'Commodity',
                'verbose_name_plural': 'Commodities',
                'ordering': ['symbol'],
                'indexes': [
                    models.Index(fields=['symbol']),
                    models.Index(fields=['is_active']),
                    models.Index(fields=['last_updated']),
                ],
            },
        ),
        migrations.CreateModel(
            name='PriceData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField()),
                ('open_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('high_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('low_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('close_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('volume', models.PositiveIntegerField(blank=True, null=True)),
                ('source_data', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('commodity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prices', to='market.commodity')),
            ],
            options={
                'verbose_name': 'Price Data',
                'verbose_name_plural': 'Price Data',
                'ordering': ['-timestamp'],
                'indexes': [
                    models.Index(fields=['timestamp']),
                    models.Index(fields=['commodity', 'timestamp']),
                ],
                'unique_together': {('commodity', 'timestamp')},
            },
        ),
        migrations.CreateModel(
            name='MarketUpdate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('running', 'Running'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('task_id', models.CharField(blank=True, max_length=100, null=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('records_processed', models.PositiveIntegerField(default=0)),
                ('records_created', models.PositiveIntegerField(default=0)),
                ('records_updated', models.PositiveIntegerField(default=0)),
                ('records_failed', models.PositiveIntegerField(default=0)),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('commodity', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updates', to='market.commodity')),
                ('data_source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='updates', to='market.datasource')),
            ],
            options={
                'verbose_name': 'Market Update',
                'verbose_name_plural': 'Market Updates',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['status']),
                    models.Index(fields=['created_at']),
                    models.Index(fields=['data_source', 'created_at']),
                ],
            },
        ),
    ] 