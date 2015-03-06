import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core import urlresolvers
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from tastypie.models import create_api_key
from lib.unique_slugify import unique_slugify
from mpowering.analytics.models import UserLocationVisualization

models.signals.post_save.connect(create_api_key, sender=User)


# Create your models here.
      
# Resource
class Resource (models.Model):
    REJECTED = 'rejected'
    PENDING_CRT = 'pending_crt'
    PENDING_MRT = 'pending_mrt'
    APPROVED = 'approved'
    STATUS_TYPES = (
        (REJECTED, _('Rejected')),
        (PENDING_CRT, _('Pending CRT')),
        (PENDING_MRT, _('Pending MRT')),
        (APPROVED, _('Approved')),
    )
    
    title = models.TextField(blank=False, null=False)
    description = models.TextField(blank=False, null=False) 
    image = models.ImageField(upload_to='resourceimage/%Y/%m/%d', max_length=200, blank=True, null=True)
    status = models.CharField(max_length=50,choices=STATUS_TYPES)
    create_date = models.DateTimeField(auto_now_add=True)
    create_user = models.ForeignKey(User, related_name='resource_create_user')
    update_date = models.DateTimeField(auto_now=True) 
    update_user = models.ForeignKey(User, related_name='resource_update_user')
    slug = models.CharField(blank=True, null=True, max_length=100)
    
    class Meta:
        verbose_name = _('Resource')
        verbose_name_plural = _('Resources')
        
    def __unicode__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        unique_slugify(self, self.title)
        super(Resource, self).save(*args, **kwargs)
    
    def get_organisations(self):
        return Tag.objects.filter(resourcetag__resource=self,category__slug='organisation')
    
    def get_files(self):
        return ResourceFile.objects.filter(resource=self)
    
    def get_urls(self):
        return ResourceURL.objects.filter(resource=self)
    
    def get_categories(self):
        categories = Category.objects.filter(tag__resourcetag__resource=self).distinct().order_by('order_by')
        for c in categories:
            c.tags = Tag.objects.filter(resourcetag__resource=self, category=c)
        return categories
    
    def get_category(self, category_slug):
        tags = Tag.objects.filter(resourcetag__resource=self, category__slug=category_slug)
        return tags
    
    def get_type_tags(self):
        tags = Tag.objects.filter(resourcetag__resource=self, category__slug='type')
        return tags
    
    def get_absolute_url(self):
        return urlresolvers.reverse('mpowering_resource', args=[self.slug])
    
    def get_edit_url(self):
        return urlresolvers.reverse('mpowering_resource_edit', args=[self.id])
    
    def tags(self):
        return Tag.objects.filter(resourcetag__resource = self)
    
    def get_no_hits(self):
        anon = ResourceTracker.objects.filter(resource=self, user=None).values_list('ip', 
                                      flat=True).distinct().count()
        identified = ResourceTracker.objects.filter(resource=self).exclude(user=None).values_list('user', 
                                      flat=True).distinct().count()                              
        return anon + identified
        
# ResourceURL
class ResourceURL (models.Model):
    url = models.URLField(blank=False, null=False, max_length=500)
    resource = models.ForeignKey(Resource)
    title = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True) 
    create_date = models.DateTimeField(auto_now_add=True)
    create_user = models.ForeignKey(User, related_name='resource_url_create_user')
    update_date = models.DateTimeField(auto_now=True) 
    update_user = models.ForeignKey(User, related_name='resource_url_update_user')

    def __unicode__(self):
        if self.description is None:
            return self.url
        else:
            return self.description
        
        
# ResourceFile
class ResourceFile (models.Model):
    file = models.FileField(upload_to='resource/%Y/%m/%d', max_length=200)
    resource = models.ForeignKey(Resource)
    title = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True) 
    create_date = models.DateTimeField(auto_now_add=True)
    create_user = models.ForeignKey(User, related_name='resource_file_create_user')
    update_date = models.DateTimeField(auto_now=True) 
    update_user = models.ForeignKey(User, related_name='resource_file_update_user')
    file_full_text = models.TextField(blank=True, null=True, default=None)
    
    def filename(self):
        return os.path.basename(self.file.name)
    
    def filesize(self):
        return os.path.getsize(settings.MEDIA_ROOT + self.file.name)
        
# ResourceRelationship
class ResourceRelationship (models.Model):
    RELATIONSHIP_TYPES = (
        ('is_translation_of', _('is translation of')),
        ('is_derivative_of', _('is derivative of')),
        ('is_contained_in', _('is contained in')),
    )
    
    resource = models.ForeignKey(Resource, related_name='resource')
    resource_related = models.ForeignKey(Resource, related_name='resource_related')
    relationship_type = models.CharField(max_length=50,choices=RELATIONSHIP_TYPES)
    description = models.TextField(blank=False, null=False) 
    create_date = models.DateTimeField(auto_now_add=True)
    create_user = models.ForeignKey(User, related_name='resource_relationship_create_user')
    update_date = models.DateTimeField(auto_now=True) 
    update_user = models.ForeignKey(User, related_name='resource_relationship_update_user')
    
# Category
class Category (models.Model):
    name = models.CharField(blank=False, null=False, max_length=100) 
    top_level = models.BooleanField(null=False,default=False)
    slug = models.CharField(blank=True, null=True, max_length=100) 
    order_by = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        
    def __unicode__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # If there is not already a slug in place...
        if not self.slug:
            # Call this slug function on the field you want the slug to be made of
            unique_slugify(self, self.name)
        # Call the rest of the old save() method
        super(Category, self).save(*args, **kwargs)
        
            
# Tag
class Tag (models.Model):
    category = models.ForeignKey(Category)
    parent_tag = models.ForeignKey('self', blank=True, null=True, default=None)
    name = models.CharField(blank=False, null=False, max_length=100)
    create_date = models.DateTimeField(auto_now_add=True)
    create_user = models.ForeignKey(User, related_name='tag_create_user')
    update_date = models.DateTimeField(auto_now=True) 
    update_user = models.ForeignKey(User, related_name='tag_update_user')
    image = models.ImageField(upload_to='tag/%Y/%m/%d', null=True, blank=True)
    slug = models.CharField(blank=True, null=True, max_length=100)
    order_by = models.IntegerField(default=0)
    external_url =  models.URLField(blank=True, null=True, default=None, max_length=500)
    description = models.TextField(blank=True, null=True, default=None)
    summary = models.CharField(blank=True, null=True, max_length=100)
    
    class Meta:
        verbose_name = _('Tag')
        verbose_name_plural = _('Tags')
        
    def __unicode__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            unique_slugify(self, self.name)
        super(Tag, self).save(*args, **kwargs)
     
    def image_filename(self):
        return os.path.basename(self.image.name)
       
# ResourceTag
class ResourceTag (models.Model):
    resource = models.ForeignKey(Resource)
    tag = models.ForeignKey(Tag)
    create_date = models.DateTimeField(auto_now_add=True)
    create_user = models.ForeignKey(User, related_name='resourcetag_create_user')    

# UserProfile
class UserProfile (models.Model):
    user = models.OneToOneField(User)
    about = models.TextField(blank=True, null=True, default=None)
    job_title = models.TextField(blank=True, null=True, default=None)
    organisation = models.ForeignKey(Tag)
    phone_number = models.TextField(blank=True, null=True, default=None)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
        
class ResourceTracker(models.Model):
    VIEW = 'view'
    VIEW_API = 'view-api'
    EDIT = 'edit'
    DOWNLOAD = 'download'
    CREATE = 'create'
    TRACKER_TYPES = (
        (VIEW, _(u'View')),
        (VIEW_API, _(u'View-api')),
        (EDIT, _(u'Edit')),
        (DOWNLOAD, _(u'Download')),
        (CREATE, _(u'Create')),
    )
    user = models.ForeignKey(User, blank=True, null=True, default=None)
    type = models.CharField(max_length=50,choices=TRACKER_TYPES, default=VIEW)
    resource = models.ForeignKey(Resource, blank=True, null=True, default=None)
    resource_file = models.ForeignKey(ResourceFile, blank=True, null=True, default=None)
    resource_url = models.ForeignKey(ResourceURL, blank=True, null=True, default=None)
    access_date = models.DateTimeField(auto_now_add=True)
    ip = models.IPAddressField(blank=True, null=True, default=None)
    user_agent = models.TextField(blank=True, null=True, default=None)
    extra_data = models.TextField(blank=True, null=True, default=None)
    
    def get_location(self):
        try:
            return UserLocationVisualization.objects.filter(ip=self.ip).first()
        except UserLocationVisualization.DoesNotExist:
            return None
class SearchTracker(models.Model):
    SEARCH = 'search'
    SEARCH_API = 'search-api'
    SEARCH_TYPES = (
        (SEARCH, _(u'search')),
        (SEARCH_API, _(u'search-api')),
    )
    user = models.ForeignKey(User, blank=True, null=True, default=None)
    query = models.TextField(blank=True, null=True, default=None)
    no_results = models.IntegerField(blank=True, null=True, default=0)
    access_date = models.DateTimeField(auto_now_add=True)
    ip = models.IPAddressField(blank=True, null=True, default=None)
    user_agent = models.TextField(blank=True, null=True, default=None)
    type = models.CharField(max_length=50,choices=SEARCH_TYPES, default=SEARCH)
    
class ResourceRating(models.Model):
    user = models.ForeignKey(User, blank=False, null=False)
    resource = models.ForeignKey(Resource, blank=False, null=False)
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True) 
    rating = models.IntegerField(validators=[MinValueValidator(1),MaxValueValidator(5)])
    comments = models.TextField(blank=True, null=True, default=None)
    
    
