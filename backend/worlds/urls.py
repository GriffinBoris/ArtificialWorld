from django.urls import path
from worlds import views

app_name = 'worlds'

urlpatterns = [
	path(
		'<uuid:world_id>/inhabitants/<uuid:actor_id>/observe/',
		views.InhabitantObservationView.as_view(),
		name='inhabitant-observe',
	),
	path(
		'<uuid:world_id>/inhabitants/<uuid:actor_id>/profile/',
		views.InhabitantProfileView.as_view(),
		name='inhabitant-profile',
	),
	path('<uuid:world_id>/messages/', views.WorldMessagesView.as_view(), name='world-messages'),
	path(
		'<uuid:world_id>/inhabitants/<uuid:actor_id>/actions/',
		views.InhabitantActionView.as_view(),
		name='inhabitant-action',
	),
	path(
		'<uuid:world_id>/inhabitants/<uuid:actor_id>/memories/',
		views.InhabitantMemoryView.as_view(),
		name='inhabitant-memory',
	),
	path(
		'<uuid:world_id>/inhabitants/<uuid:actor_id>/artifacts/<uuid:artifact_id>/',
		views.InhabitantDocumentView.as_view(),
		name='inhabitant-document',
	),
	path('', views.WorldListView.as_view(), name='world-list'),
	path('<uuid:world_id>/', views.WorldDetailView.as_view(), name='world-detail'),
	path('<uuid:world_id>/terrain/', views.WorldTerrainView.as_view(), name='world-terrain'),
	path('<uuid:world_id>/step/', views.WorldStepView.as_view(), name='world-step'),
	path('<uuid:world_id>/status/', views.WorldStatusView.as_view(), name='world-status'),
	path('<uuid:world_id>/events/', views.WorldEventsView.as_view(), name='world-events'),
	path('<uuid:world_id>/replay/', views.WorldReplayView.as_view(), name='world-replay'),
	path('<uuid:world_id>/motion/', views.WorldMotionView.as_view(), name='world-motion'),
	path('<uuid:world_id>/agent-settings/', views.WorldAgentSettingsView.as_view(), name='world-agent-settings'),
	path('<uuid:world_id>/edit/', views.WorldEditView.as_view(), name='world-edit'),
	path('<uuid:world_id>/inspect/<uuid:entity_id>/', views.WorldInspectView.as_view(), name='world-inspect'),
]
