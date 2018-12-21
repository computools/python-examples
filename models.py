import markdown
import re
from jinja2 import escape
from sortedm2m.fields import SortedManyToManyField
from urllib.parse import urlparse

from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.template.defaultfilters import slugify
from django.core.urlresolvers import reverse

from sideadmin.fields import ImageUploaderField
from sideadmin.mixins import MetaModel, RelatableModel
from sideadmin.models import Block, BaseImageBlock, Image, Video
from sideadmin.social import Social
from sideadmin.utils import generate_image_path
from sidecart.products.models import Product, Variation
from sidecart.registration.mixins import BaseProduct
from sideteam.models import BaseMember, Category
from sidetools.mantles.models import BaseMantle
from sidepost.mixins import MarkdownMixin
from storelocator.models import Location as StorelocatorLocation

from .mixins import AnchorMixin, TwoColumnLayoutMixin


class Mantle(BaseMantle):
	AUTOPLAY_VIDEO = 'autoplay-video'
	CENTER_TOP = 'feature--center feature--top'
	CENTER_MIDDLE = 'feature--center feature--middle'
	CENTER_BOTTOM = 'feature--bottom feature--center'
	LEFT_TOP = 'feature--left feature--top'
	LEFT_MIDDLE = 'feature--left feature--middle'
	LEFT_BOTTOM = 'feature--bottom feature--left'
	RIGHT_TOP = 'feature--right feature--top'
	RIGHT_MIDDLE = 'feature--middle feature--right'
	RIGHT_BOTTOM = 'feature--bottom feature--right'
	TEMPLATES = (
		(CENTER_TOP, 'Center Top'),
		(CENTER_MIDDLE, 'Center Middle'),
		(CENTER_BOTTOM, 'Center Bottom'),
		(LEFT_TOP, 'Left Top'),
		(LEFT_MIDDLE, 'Left Middle'),
		(LEFT_BOTTOM, 'Left Bottom'),
		(RIGHT_TOP, 'Right Top'),
		(RIGHT_MIDDLE, 'Right Middle'),
		(RIGHT_BOTTOM, 'Right Bottom')
	)
	VIDEO = 'video'
	mobile_image = ImageUploaderField(upload_to=generate_image_path)
	template = models.CharField(max_length=50, choices=TEMPLATES, default=LEFT_BOTTOM)
	text_hex = models.CharField(max_length=6, blank=True, null=True)
	videos = GenericRelation(Video)


class Member(BaseMember):
	quote = models.TextField(blank=True)
	categories = models.ManyToManyField(Category, blank=True)
	gallery = GenericRelation(Image)
	videos = GenericRelation(Video)
	facebook = models.CharField(max_length=255, null=True, blank=True, help_text="Facebook username")
	instagram = models.CharField(max_length=255, null=True, blank=True, help_text="Instagram username")
	twitter = models.CharField(max_length=255, null=True, blank=True, help_text="Twitter username")
	google_plus = models.CharField(max_length=255, null=True, blank=True, help_text="Google Plus username")
	tumblr = models.CharField(max_length=255, null=True, blank=True, help_text="Tumblr username")
	website = models.URLField(null=True, blank=True, default=None)
	job_title = models.CharField(max_length=255, null=True, blank=True, default=None, help_text='Comma separated list of values')
	home_town = models.CharField(max_length=255, null=True, blank=True, default=None)
	excerpt = models.TextField(blank=True)

	search_fields = ('name', 'content')
	search_suggestion_fields = ('name',)
	search_tile_macro = 'ambassador_tile'

	def category(self):
		return self.categories.first()

	@classmethod
	def search_queryset(cls):
		return cls.objects.public()

	def social_accounts(self):
		accounts = []
		networks = sorted(Social.networks, key=lambda x: Social.networks[x]['sort'])
		for network in networks:
			account = getattr(self, slugify(network).replace('-', '_'), None)
			if account:
				accounts.append({
					'name': network,
					'slug': slugify(network),
					'account': account,
					'url': Social.url(network, account),
				})
		if self.website:
			accounts.append({
				'name': '',
				'slug': slugify('Website'),
				'account': urlparse(self.website).netloc,
				'url': self.website,
			})
		return accounts

	def html(self, filter=None, field_name=False):
		return markdown.markdown(getattr(self, field_name, 'content') if field_name else self.content, ['extra'])


class FeaturedCategory(BaseImageBlock, Block):
	subtitle = models.CharField(max_length=250, blank=True, null=True)
	url_label = models.TextField(blank=True, null=True)
	admin = 'goalzero.admin.FeaturedCategoryAdmin'

	class Meta:
			pass

	def url(self):
		return self.url


class FeaturedBlock(BaseImageBlock, Block):
	CENTER_TOP = 'feature--center feature--top'
	CENTER_MIDDLE = 'feature--center feature--middle'
	CENTER_BOTTOM = 'feature--bottom feature--center'
	LEFT_TOP = 'feature--left feature--top'
	LEFT_MIDDLE = 'feature--left feature--middle'
	LEFT_BOTTOM = 'feature--bottom feature--left'
	RIGHT_TOP = 'feature--right feature--top'
	RIGHT_MIDDLE = 'feature--middle feature--right'
	RIGHT_BOTTOM = 'feature--bottom feature--right'
	TEMPLATES = (
		(CENTER_TOP, 'Center Top'),
		(CENTER_MIDDLE, 'Center Middle'),
		(CENTER_BOTTOM, 'Center Bottom'),
		(LEFT_TOP, 'Left Top'),
		(LEFT_MIDDLE, 'Left Middle'),
		(LEFT_BOTTOM, 'Left Bottom'),
		(RIGHT_TOP, 'Right Top'),
		(RIGHT_MIDDLE, 'Right Middle'),
		(RIGHT_BOTTOM, 'Right Bottom')
	)
	template_position = models.CharField(max_length=50, choices=TEMPLATES, default=CENTER_MIDDLE)
	text_hex = models.CharField(max_length=6, blank=True, null=True)
	subtitle = models.CharField(max_length=100, blank=True, null=True)
	description = models.TextField(blank=True, null=True)
	url_label = models.TextField(blank=True, null=True)
	video_url = models.URLField(blank=True,)

	admin = 'goalzero.admin.FeaturedBlockAdmin'
	template = 'goalzero/blocks/{}.jinja'

	class Meta:
			pass


class Quote(BaseImageBlock, Block):
	copy = models.CharField(max_length=200, blank=True, null=True)
	author = models.CharField(max_length=200, blank=True, null=True)
	background_hex = models.CharField(max_length=6, blank=True, null=True)
	text_hex = models.CharField(max_length=6, blank=True, null=True)

	admin = 'goalzero.admin.QuoteAdmin'
	template = 'goalzero/blocks/{}.jinja'

	class Meta:
			pass

	def url(self):
		return self.url


class ProductFeaturesBlock(BaseImageBlock, Block):
	description = models.TextField(blank=True, null=True)
	url_label = models.TextField(blank=True, null=True)

	admin = 'goalzero.admin.ProductFeaturesBlockAdmin'
	template = 'goalzero/blocks/{}.jinja'

	class Meta:
			pass

	def url(self):
		return self.url


class ProductFeature(models.Model):
	text = models.TextField(blank=True, null=True)
	image = ImageUploaderField(upload_to=generate_image_path)
	block = models.ForeignKey(ProductFeaturesBlock, on_delete=models.CASCADE)

	@property
	def content_type_id(self):
		return ContentType.objects.get(model=self.__class__.__name__.lower()).id

	@property
	def image_path(self):
		return 'product_feature/{}'.format(self.id)


class TitleTextBlock(BaseImageBlock, Block):
	description = models.TextField(blank=True, null=True)

	admin = 'goalzero.admin.TitleTextAdmin'
	template = 'goalzero/blocks/{}.jinja'

	class Meta:
			pass

	def url(self):
		return self.url


class ProductFeatureCategory(MetaModel):
	name = models.CharField(max_length=100)
	slug = models.SlugField(unique=True)
	image = ImageUploaderField(upload_to=generate_image_path)

	class Meta:
		verbose_name_plural = "PRODUCT FEATURE CATEGORIES"

	def __str__(self):
		return self.name.title()

	@property
	def image_path(self):
		return 'product_feature_category/{}'.format(self.id)

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.name)
		super(ProductFeatureCategory, self).save(*args, **kwargs)


class FeaturedPage(MetaModel, RelatableModel):
	name = models.CharField(max_length=100)
	slug = models.SlugField(unique=True)
	thumbnail = ImageUploaderField(upload_to=generate_image_path)
	generate_menu = models.BooleanField(default=True, verbose_name='Show Page Navigaiton')
	feature_category = SortedManyToManyField(ProductFeatureCategory, related_name='pages', blank=True)
	related_models = (('mantle', 'goalzero.mantle'), ('related_products', 'products.product'), ('blocks', 'sideadmin.block'))

	def get_absolute_url(self):
		return self.url()

	def __str__(self):
		return self.name

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.name)
		super(FeaturedPage, self).save(*args, **kwargs)

	def get_menu_items(self):
		if not self.generate_menu:
			return []

		menu_items = [{'url': '#{}'.format(block.anchor), 'name': block.menu_name} for block in self.related("blocks") if getattr(block, 'anchor', False)]

		if self.related('related_products'):
			menu_items.append({'url': "#buy", 'name': 'Buy'})

		return menu_items

	@property
	def image_path(self):
		return 'featured_page/{}'.format(self.id)

	@property
	def content_type_id(self):
		return ContentType.objects.get(model=self.__class__.__name__.lower()).id

	def meta_description(self):
		return self.meta('page_description') or self.html()

	def meta_title(self):
		return self.meta('page_title') or self.name

	def url(self):
		return reverse('product_features', args=[self.slug])

class ChargeTimeBlock(Block, AnchorMixin):
	title = models.CharField(max_length=100)
	products = SortedManyToManyField(Product)
	faq = models.TextField(blank=True, null=True)

	admin = 'goalzero.admin.ChargeTimeBlockAdmin'
	template = 'goalzero/blocks/{}.jinja'

	def thumb(self):
		return ""

	def __str__(self):
		return self.title


_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')


class ComparisonChartBlock(BaseImageBlock, Block, AnchorMixin):
	POSITION_CHOICES = (
		(1, 'left'),
		(2, 'center'),
		(3, 'right'),
	)

	button_place = models.IntegerField(choices=POSITION_CHOICES, default=1)
	left_column_title = models.CharField(max_length=150, blank=True, null=True)
	left_column_content = models.TextField(blank=True, null=True)
	right_column_title = models.CharField(max_length=150, blank=True, null=True)
	right_column_content = models.TextField(blank=True, null=True)

	right_image = ImageUploaderField(upload_to=generate_image_path, blank=True, null=True, help_text="Will display when selected Center button place.")

	admin = 'goalzero.admin.ComparisonChartBlockAdmin'
	template = 'goalzero/blocks/{}.jinja'

	class Meta:
			pass

	@property
	def image_path(self):
		return 'comparison_chart_block/{}'.format(self.id)

	def url(self):
		return self.url

	def get_left_items(self):
		iterator = iter(_paragraph_re.split(escape(self.left_column_content)))
		return {
			'name': self.left_column_title,
			'compare_items': list(zip(iterator, iterator))
		}

	def get_right_items(self):
		iterator = iter(_paragraph_re.split(escape(self.right_column_content)))
		return {
			'name': self.right_column_title,
			'compare_items': list(zip(iterator, iterator))
		}


class SplitBlock(BaseImageBlock, Block, AnchorMixin):
	DESCRIPTION_TYPES = (
		(1, 'Plain Text'),
		(2, 'Unordered List'),
		(3, 'Ordered List'),
	)

	POSITION_CHOICES = (
		(1, 'left'),
		(2, 'right'),
	)

	url_label = models.TextField(blank=True, null=True)
	description = models.TextField(blank=True, null=True)
	layout_description_type = models.IntegerField(choices=DESCRIPTION_TYPES, default=1)
	layout_description_place = models.IntegerField(choices=POSITION_CHOICES, default=1)
	background_color = models.CharField(max_length=6, blank=True, null=True)

	admin = 'goalzero.admin.SplitBlockAdmin'
	template = 'goalzero/blocks/{}.jinja'

	def get_description_items(self):
		return _paragraph_re.split(escape(self.description))


class FeaturedProductsBlock(Block):
	title = models.CharField(max_length=100)
	url_label = models.CharField(max_length=200)
	url = models.CharField(max_length=100)
	products = SortedManyToManyField(Product)

	admin = 'goalzero.admin.FeaturedProductsBlockAdmin'
	template = 'goalzero/blocks/{}.jinja'

	def thumb(self):
		return ""

	def __str__(self):
		return self.title


class TextBlock(Block, MarkdownMixin):
	title = models.CharField(max_length=200)
	content = models.TextField(null=True, blank=True)

	admin = 'goalzero.admin.TextBlockAdmin'
	template = 'goalzero/blocks/{}.jinja'

	def thumb(self):
		return ""

	def __str__(self):
		return self.title



class GalleryBlock(Block, AnchorMixin):
	gallery = GenericRelation(Image)

	admin = 'goalzero.admin.GalleryBlockAdmin'
	template = 'goalzero/blocks/{}.jinja'

	@property
	def image_path(self):
		return 'gallery_block/{}'.format(self.id)

	def thumb(self):
		return self.gallery.first()


class VideoBlock(BaseImageBlock, Block, AnchorMixin):
	video = GenericRelation(Video)

	admin = 'goalzero.admin.VideoBlockAdmin'
	template = 'goalzero/blocks/{}.jinja'

	def url(self):
		return self.url


class ProductLineBlock(Block, AnchorMixin):
	products = SortedManyToManyField(Product)

	admin = 'goalzero.admin.ProductLineBlockAdmin'
	template = 'goalzero/blocks/{}.jinja'

	def thumb(self):
		return ""

	def __str__(self):
		return self.name


class FounderBlock(Block):
	title = models.CharField(max_length=200, blank=True)
	sub_title = models.CharField(max_length=200, blank=True)
	background_image = ImageUploaderField(upload_to=generate_image_path, blank=True)
	thumbnail_image = ImageUploaderField(upload_to=generate_image_path, blank=True)
	quote_founder = models.CharField(max_length=500, blank=True)
	description = models.TextField(null=True, blank=True)
	signature_image = ImageUploaderField(upload_to=generate_image_path, blank=True)
	signature_name = models.CharField(max_length=200, blank=True)

	admin = 'goalzero.admin.FounderBlockAdmin'
	template = 'goalzero/blocks/{}.jinja'

	class Meta:
		pass

	def url(self):
		return self.url

	@property
	def image_path(self):
		return 'founder_block/{}'.format(self.id)

	def thumb(self):
		return ""

	def html(self, filter=None, field_name=False):
		return markdown.markdown(getattr(self, field_name, 'description') if field_name else self.description, ['extra'])

	def __str__(self):
		return self.title


class CostcoRoadShow(StorelocatorLocation):
	start_date = models.DateTimeField()
	end_date = models.DateTimeField()


class RegistrationProduct(BaseProduct):
	registration = models.ForeignKey('registration.Registration', related_name="registration_product")
	serial_number = models.CharField(max_length=200, blank=True)
