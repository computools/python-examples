import collections
import json
import pytz
from geopy.exc import GeocoderQuotaExceeded
from geopy.geocoders import GoogleV3
from dateutil.relativedelta import relativedelta
from datetime import datetime

from django.contrib.messages import success, error
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings
from django.core.exceptions import FieldError
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _

from sidecart.core.decorators import region_allows
from sidecart.core.middleware import CartMiddleware
from sidecart.products.models import Category, Product, Variation, Item
from sidecart.registration.views import index as registration_index
from sidepost.models import Page, Post, Category as PostCategory
from sidepost.views.posts import detail as blog_detail, default_context as blog_default_context
from sidecart.orders.views import cart
from sidecart.orders.signals import cart_change
from storelocator.models import Location, Category as LocatorCategory
from storelocator.serializers import LocationSerializer

from .models import FeaturedPage, Member, CostcoRoadShow


def contact(request):
	"Contact form page"
	try:
		page = Page.objects.get(slug='contact')
	except Page.DoesNotExist:
		raise Page.DoesNotExist('Contact page missing!')
	context = {
		'page': page,
	}

	if request.method == 'POST':
		form = ContactForm(request.POST)
		if form.is_valid():
			message = render_to_string('goalzero/emails/contact.jinja', form.cleaned_data)
			send_mail('Goal Zero Website Contact Form Submission', message, form.cleaned_data['email'], (settings.Company.email,))
			success(request, "Your message has been sent! Thanks for contacting us, we'll be in touch with you soon.")
			context['success'] = True
	else:
		form = ContactForm()

	context.update({'form': form})
	return TemplateResponse(request, 'sidepost/pages/contact.jinja', context)


def home(request):
	try:
		page = Page.objects.get(slug='home')
	except Page.DoesNotExist:
		raise Page.DoesNotExist('Home pages missing!')
	context = {
		'page': page,
		'mantles': page.related('mantle')
	}
	return TemplateResponse(request, 'goalzero/home.jinja', context)


def product_landing(request):
	try:
		page = Page.objects.get(slug='product-landing')
	except Page.DoesNotExist:
		raise Page.DoesNotExist('Product Landing pages missing!')

	categories = Category.objects.filter(parent__slug='shop')
	for category in categories:
		category.prefetched_products = Product.objects.public().filter(categories=category)[:3]

	context = {
		'page': page,
		'mantles': page.related('mantle'),
		'categories': categories
	}
	return TemplateResponse(request, 'goalzero/product_landing.jinja', context)


@region_allows('shopping')
def add_to_cart_override(request):
	if 'wishlist' in request.POST:
		return cart.wishlist.add(request)
	update = True
	vars = None
	variation = None

	# Add to cart
	added_items = []

	items_to_cart = [{'item_id': request.POST.get('item_id'), 'product_id': request.POST.get('product_id'), 'quantity': request.POST.get('quantity', 1)}]

	items_to_cart += [{'item_id': essential[1]} for essential in filter(lambda item: item[0].startswith('essential'), request.POST.items())]

	try:
		for item in items_to_cart:

			"Adding items to carts"

			quantity = int(item.get('quantity', 1))
			item_id = int(item.get('item_id')) if item.get('item_id', None) else None
			variation_id = int(item.get('product_id')) if item.get('product_id', None) else None
			# Wishlist request instead of cart

			request.cart.previous_items = list(request.cart.items.all())

			# Find product
			try:
				variation = Variation.objects.public().get(id=variation_id)
			except Variation.DoesNotExist:
				pass

			# Find item
			if variation:
				if variation.has_items:
					if not item_id:
						raise AttributeError(_("Please select a size!"))
					item = get_object_or_404(Item, id=item_id)
				else:
					item = variation.item_set.first()
			else:
				item = get_object_or_404(Item, id=item_id)

			added_items.append(request.cart.add(item, quantity, update=update, vars=vars or {}))

		cart_change.send(sender='cart.change', cart=request.cart, request=request)

		success(request, _('Added to your {label}!').format(label=request.cart.CART_LABEL.lower()))
		response = redirect('cart')

		# If requested through AJAX, return results
		if request.is_ajax():
			CartMiddleware.reload_cart(request)
			response = TemplateResponse(request, 'sidecart/orders/cart_mini.jinja',
										{'added_items': added_items, 'quantity': quantity})
	except Exception as exp:
		error(request, _('Error adding that to your {label}: {exp}').format(label=request.cart.CART_LABEL.lower(), exp=exp))
		response = redirect(variation.url())

	# Otherwise redirect to the right place
	return response


def storelocator_index(request, category_slug=None, product_slug=None, variation_slug=None, item_slug=None):

	# Grab location from POST or session
	query = request.GET.get('location', '')
	radius = int(request.GET.get('radius', 25))
	date = request.GET.get('date', None)
	if date:
		date = datetime.strptime(date, '%Y-%m-%d')
	locality = int(request.GET.get('locality', 1))

	location = None
	stores = []
	closest = False
	result = None

	# Geocode location
	if query:
		try:
			result = GoogleV3(api_key=settings.Site.google_api_key).geocode(query)
		except GeocoderQuotaExceeded:
			error(request, "Our geocoder is currently overloaded - please try again later!")
		else:
			try:
				location = (result.point.latitude, result.point.longitude)
				query = result.address
			except AttributeError:
				error(request, "We could not find that location!")

	product = None
	variation = None
	item = None
	variations = None
	filterset = None
	filters = None
	category = None

	try:
		from sidecart.products.models import Product, Variation
		from sidecart.products.filters import FilterSet

		if product_slug:
			product = Product.objects.filter(slug=product_slug).first()
			if not product:
				return redirect('storelocator')
			if variation_slug:
				variation = product.variations().filter(slug=variation_slug).first()
				if not variation:
					return redirect('storelocator', product_slug)
				if item_slug:
					item = variation.items().filter(slug=item_slug).first()
					if not item:
						return redirect('storelocator', product_slug, variation_slug)
		elif settings.STORELOCATOR_INCLUDE_FILTERS:
			filters = request.GET.get('filters', None)
			if filters == '/':
				filters = None
			variations = None if not filters else Variation.objects.public().select_related('product').prefetch_related('product__categories')
			try:
				filterset = FilterSet(variations, filters.split('/') if filters else [])
			except KeyError:
				filters = None
			if filters:
				variations = filterset.apply()
	except (ImportError, FieldError):
		if product_slug:
			return redirect('storelocator')

	if category_slug == 'costco-roadshow':
		category = get_object_or_404(LocatorCategory, slug=category_slug, active=True)
		stores = CostcoRoadShow.objects.exclude(online=True).filter(locality=locality)
		if date:
			stores = stores.filter((Q(start_date__month=date.month) & Q(start_date__year=date.year)) |
									(Q(end_date__month=date.month) & Q(end_date__year=date.year)))
	else:
		# Grab nearby locations
		if location:
			all_stores = Location.objects.active().exclude(online=True)
			if category_slug:
				category = get_object_or_404(LocatorCategory, slug=category_slug, active=True)
				all_stores = all_stores.filter(categories__in=category.get_descendants(include_self=True))
			stores = all_stores.within_radius(location, radius=radius)
			if product_slug or filters:
				stores = stores.with_inventory(variations, product_slug, variation_slug, item_slug)
			if not stores:
				if not product_slug and not filters:
					stores = all_stores.order_by_distance_from(location)[:1]
					closest = True
			else:
				stores = sorted(stores, key=lambda l: l.distance_from(location).km)
		elif settings.STORELOCATOR_ALWAYS_LOAD_ALL_STORES:
			stores = Location.objects.active()

	# Set context
	context = {
		'success': True if location else False,
		'location': {
			'lat': location[0] if location else '39.8282',
			'lng': location[1] if location else '-98.5795',
		},
		'stores': LocationSerializer(stores, many=True, origin=location, query=query).data if request.is_ajax() else stores,
		'query': query,
		'closest': closest,
		'radius': radius
	}

	# json serializer doesn't like addresses and decimals

	# Return response
	if request.is_ajax():
		response = HttpResponse(json.dumps(context), content_type='application/json')
	else:
		for store in context['stores']:
			store.distance = int(store.distance_from(location).miles)
		context['product'] = product
		context['variation'] = variation
		context['item'] = item
		context['filterset'] = filterset
		context['filters'] = filters
		context['categories'] = LocatorCategory.objects.active()
		context['category'] = category if category else LocatorCategory.objects.active().all().first()
		context['online_stores'] = Location.objects.active().online().order_by('name')

		if category_slug == 'costco-roadshow':
			costco_dates = CostcoRoadShow.objects.exclude(online=True).order_by('start_date').values_list('start_date', 'end_date')
			display_dates = {}
			for date in costco_dates:
				display_dates[datetime(year=date[0].year, month=date[0].month, day=1)] = 1
				display_dates[datetime(year=date[1].year, month=date[1].month, day=1)] = 1

			context['dates'] = list(sorted(display_dates.items(), key=lambda t: t[0]))
			context['date'] = request.GET.get('date', '')
			context['states'] = CostcoRoadShow.objects.exclude(online=True).prefetch_related('locality').order_by('locality').values_list('locality__name', 'locality__id').distinct()
			context['locality'] = locality

		try:
			context['page'] = Page.objects.public().get(slug='find-a-store')
		except Page.DoesNotExist:
			pass
		response = TemplateResponse(request, 'storelocator/index.jinja', context)

	return response


def storelocator_url_resolver_override(request, *args, **kwargs):
	# Split by slash and remove last empty element
	args = args[0].rstrip('/').split('/')
	try:
		product_args = args[:4]
		if len(product_args) < 1 or len(product_args) > 4:
			raise Http404
		return storelocator_index(request, *product_args, **kwargs)
	except Http404:
		return storelocator_index(request, args)


def get_sort(request):
	sort = request.session.get('blog_sort', settings.SIDEPOST_POSTS_DEFAULT_SORT)
	keys = {s.key: s for s in getattr(settings, 'SIDEPOST_POSTS_SORTS')}
	if request.GET.get('blog_sort') and request.GET['blog_sort'] in keys:
		sort = request.GET['blog_sort']
		request.session['blog_sort'] = sort
	return keys.get(sort, settings.SIDEPOST_POSTS_DEFAULT_SORT)


def blog_index(request, category_path=None, page=1, year=None, month=None, featured_override=False):
	context = blog_default_context()
	current_sort = get_sort(request)

	excluded_categories = PostCategory.objects.filter(slug__in=['history']).values_list('pk', flat=True)

	context['categories'] = context['categories'].exclude(pk__in=excluded_categories)

	if category_path:
		category = None
		for category_slug in category_path:
			category = get_object_or_404(PostCategory, slug=category_slug, parent=category)
		context['category'] = category
		posts = category.posts().public().distinct()
	else:
		posts = Post.objects.public().distinct()

	posts = posts.exclude(categories__in=excluded_categories)

	if year:
		try:
			start_date = datetime(int(year), int(month) if month else 1, 1, tzinfo=pytz.utc)
			end_date = start_date + (relativedelta(months=1) if month else relativedelta(years=1))
			posts = posts.filter(publish_date__range=(start_date, end_date))
		except ValueError:
			raise Http404

	posts = posts.prefetch_related('categories')

	posts = posts.order_by(current_sort.posts_order)

	featured_count = featured_override if featured_override is not False else int(settings.Blog.features)
	# Allow other views to override the number of featured posts so we can get all of the posts
	if featured_count:
		features, posts = (posts[:featured_count], posts[featured_count:])
		context['features'] = features

	# Allow other views to override the posts_per_page value, fall back to the setting
	paginator = Paginator(posts, getattr(request, 'posts_per_page', settings.Blog.posts_per_page))

	try:
		posts = paginator.page(page)
	except PageNotAnInteger:
		posts = paginator.page(1)
	except EmptyPage:
		posts = paginator.page(paginator.num_pages)

	context['paginator'] = paginator
	context['posts'] = posts
	context['year'] = year
	context['month'] = month
	context['current_sort'] = current_sort
	context['blog_sorts'] = settings.SIDEPOST_POSTS_SORTS,

	try:
		page = Page.objects.public().get(slug='blog-landing')
		context['page'] = page
	except Page.DoesNotExist:
		pass

	return TemplateResponse(request, 'sidepost/posts/index.jinja', context)


def blog_url_resolver_override(request, *args, **kwargs):
	# Split by slash and remove last empty element
	args = args[0].rstrip('/').split('/')
	try:
		if len(args) != 1:
			raise Http404
		return blog_detail(request, *args, **kwargs)
	except Http404:
		kwargs = {}
		# Handle pagination argument
		if 'page' in args:
			try:
				kwargs['page'] = args.pop(args.index('page') + 1)
			except IndexError:
				pass
			else:
				args.remove('page')
		if 'archive' in args:
			try:
				kwargs['year'] = args.pop(args.index('archive') + 1)
				kwargs['month'] = args.pop(args.index('archive') + 1)
			except IndexError:
				pass
			if 'year' in kwargs:
				args.remove('archive')
		return blog_index(request, args, **kwargs)


def product_features(request, page_slug):
	context = {	}
	try:
		page = FeaturedPage.objects.get(slug=page_slug)
		context['featured_page'] = page
	except Page.DoesNotExist:
		raise Http404

	return TemplateResponse(request, 'goalzero/product_features.jinja', context)


def story(request):
	try:
		page = Page.objects.get(slug='story')
	except Page.DoesNotExist:
		raise Page.DoesNotExist('Story page missing!')
	posts = Post.objects.public().filter(categories__slug='history').order_by('publish_date')
	posts_by_year = collections.OrderedDict()
	for post in posts:
		if posts_by_year.get(post.publish_date.year):
			posts_by_year[post.publish_date.year].append(post)
		else:
			posts_by_year[post.publish_date.year] = [post]
	context = {
		'page': page,
		'history_categories': posts_by_year,
		'story_members': Member.objects.filter(categories__name="members")
	}
	return TemplateResponse(request, 'sidepost/pages/story.jinja', context)


def how_it_works(request):
	try:
		page = Page.objects.get(slug='how-it-works')
	except Page.DoesNotExist:
		raise Page.DoesNotExist('How It Works page missing!')

	context = {
		'page': page,
		'products_data': json.dumps(dict(((v.code, (v.thumb().url, v.url())) for v in Product.objects.all() if v.thumb())))
	}
	return TemplateResponse(request, 'goalzero/how_it_works.jinja', context)


def coop(request):
	try:
		page = Page.objects.get(slug='coop')
	except Page.DoesNotExist:
		raise Page.DoesNotExist('Story page missing!')
	context = {
		'page': page,
	}
	return TemplateResponse(request, 'goalzero/coop.jinja', context)


def registration_index_override(request):
	try:
		page = Page.objects.get(slug='product-registration')
	except Page.DoesNotExist:
		raise Page.DoesNotExist('Product Registration page missing!')

	products_type = {}
	for cat in Category.objects.filter(parent__slug="shop"):
		products_type[cat.name] = [item for prod in cat.products() for item in prod.variations().values_list('name', 'code')]
	tpl = registration_index(request)
	try:
		if getattr(tpl, 'context_data'):
			tpl.context_data['products_type'] = json.dumps(products_type)
			tpl.context_data['page'] = page
	except AttributeError:
		pass
	return tpl

# BazaarVoice container page (http://knowledge.bazaarvoice.com/wp-content/conversations/en_US/KB/#Code_integration/Container_page_code.htm)
def container(request):
	return TemplateResponse(request, 'goalzero/container.jinja', {})