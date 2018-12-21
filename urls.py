from django.conf import settings
from django.conf.urls import include, patterns, url
from django.conf.urls.static import static
from django_jinja import views

import sideadmin

sideadmin.autodiscover()

# Set error pages
handler403 = views.PermissionDenied.as_view()
handler404 = views.PageNotFound.as_view()
handler500 = views.ServerError.as_view()

urlpatterns = patterns('goalzero.views',

	url(r'^blog/$', 'blog_index', name='blog_index'),
	url(r'^blog/(.+)/$', 'blog_url_resolver_override', name='blog_url_resolver_override'),
	url(r'^cart/add/$', 'add_to_cart_override', name='add_to_cart_override'),
	url(r'^contact/$', 'contact', name='contact'),
	url(r'^coop/$', 'coop', name='coop'),
	url(r'^$', 'home', name='home'),
	url(r'^how-it-works/$', 'how_it_works', name='how_it_works'),
	url(r'^kits/', include('kits.urls')),
	url(r'^product-landing/$', 'product_landing', name='product_landing'),
	url(r'^product-features/(?P<page_slug>[0-9a-z-]+)/$', 'product_features', name='product_features'),
	url(r'^product-registration/$', 'registration_index_override', name='registration'),
	url(r'^store-finder/$', 'storelocator_index', name='storelocator_index'),
	url(r'^store-finder/(.+)/$', 'storelocator_url_resolver_override', name='storelocator_url_resolver_override'),
	url(r'^story/$', 'story', name='story'),
	url(r'^how-it-works/$', 'how_it_works', name='how_it_works'),
	url(r'^coop/$', 'coop', name='coop'),
	# Kits
	url(r'^kits/', include('kits.urls')),
	url(r'^product-registration/$', 'registration_index_override', name='registration'),
	# URL for bazaarvoice container page (http://knowledge.bazaarvoice.com/wp-content/conversations/en_US/KB/#Code_integration/Container_page_code.htm)
	url(r'^container/$', 'container', name='container'),
	# url(r'^support/$', 'support', name='support'),
	# URLs used for demo purposes (delete when these are built out)
	#url(r'^about/$', 'about', name='about'),
	# url(r'^allingoodfun/$', 'allingoodfun', name='allingoodfun'),
	# url(r'^shop/$', 'shop', name='shop_landing'),
	# url(r'^stories/$', 'stories', name='stories'),
	# url(r'^videos/$', 'videos', name='videos'),

) + patterns('',

	# Newsletter
	url(r'^newsletter/', include('newsletter.urls')),

	# SideCart
	url(r'^account/', include('sidecart.customers.urls')),
	url(r'^wishlist/(?P<hashid>[^/]+)/$', 'sidecart.customers.views.wishlist.public', name='public_wishlist'),
	url(r'^track/', 'sidecart.customers.views.orders.track', name='track_order'),
	url(r'^shop/', include('sidecart.products.urls.products')),
	url(r'^cart/promotions/', include('sidecart.promotions.urls')),
	url(r'^cart/', include('sidecart.orders.urls.cart')),
	url(r'^checkout/', include('sidecart.orders.urls.checkout')),
	url(r'^giftcards/', include('sidecart.giftcards.urls')),
	url(r'^return/', include('sidecart.returns.urls')),

	# Product Registration
	url(r'^product-registration/', include('sidecart.registration.urls')),

	# SideAdmin
	url(r'^admin/', include('sideadmin.urls')),
	url(r'^admin/', include(sideadmin.site.urls)),

	# Store Locator
	url(r'^store-finder/', include('storelocator.urls')),

	# SideTeam
	url(r'^ambassadors/', include('sideteam.urls')),

	# Search
	url(r'^search/', include('sidetools.search.urls')),

	# API's
	url(r'^api/', include('sidetools.api.urls')),
	url(r'^api/', include('sidecart.customers.urls.api')),
	url(r'^api/', include('sidecart.orders.urls.api')),
	url(r'^api/', include('sidecart.products.urls.api')),
	url(r'^api/', include('sidecart.shipping.urls.api')),
	url(r'^api/', include('sidecart.returns.urls.api')),
	# url(r'^api/', include('storelocator.urls.api')),
	url(r'^api/', include('geo.urls.api')),

	# Feeds
	url(r'^feeds/', include('sidecart.products.urls.feeds')),

	# Error testing
	url(r'^error/403/$', handler403),
	url(r'^error/404/$', handler404),
	url(r'^error/500/$', handler500),
	# url(r'^access-denied/$', 'sideadmin.views.waf_denied'),

	# Email Testing
	url(r'^emails(?:/(?P<email_type>[a-zA-Z-]+))?(?:/(?P<param>[0-9]+))?/$', 'sideadmin.views.emails.email_test', name='emails'),

	# SidePost
	url(r'^blog/', include('sidepost.urls.posts')),
	url(r'^', include('sidepost.urls.pages')),
)

if settings.DEBUG:
	urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
