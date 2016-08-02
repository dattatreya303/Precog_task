from django.conf.urls import url
from . import views

app_name = 'tweets'
urlpatterns = [
	url(r'^$', views.main, name="main"),
	url(r'^info/$', views.info, name="info"),
	# url(r'^info/nodelist$', views.nodes, name="nodelist"),
	# url(r'^info/edgelist$', views.edges, name="edgelist"),
]