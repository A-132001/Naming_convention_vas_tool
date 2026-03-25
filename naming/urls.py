from django.urls import path

from naming.views import (
    AdminNamingRequestDetailView,
    AdminNamingRequestListView,
    AdminNamingRequestStep1View,
    AdminNamingRequestStep2View,
    AdminNamingRequestStep3View,
    AdminNamingRequestStep4View,
    NamingRequestFinalSubmitView,
    NamingRequestStartView,
    NamingRequestStep1EditView,
    NamingRequestStep2View,
    NamingRequestStep3View,
    NamingRequestStep4View,
)


urlpatterns = [
    # User workflow
    path("", NamingRequestStartView.as_view(), name="naming_requests_start"),
    path("new/", NamingRequestStartView.as_view(), name="naming_requests_new"),
    path("<int:pk>/step1/edit/", NamingRequestStep1EditView.as_view(), name="naming_request_step1_edit"),
    path("<int:pk>/step2/", NamingRequestStep2View.as_view(), name="naming_request_step2"),
    path("<int:pk>/step3/", NamingRequestStep3View.as_view(), name="naming_request_step3"),
    path("<int:pk>/step4/", NamingRequestStep4View.as_view(), name="naming_request_step4"),
    path("<int:pk>/final/submit/", NamingRequestFinalSubmitView.as_view(), name="naming_request_final_submit"),

    # Admin review
    path("admin/", AdminNamingRequestListView.as_view(), name="admin_naming_request_list"),
    path("admin/<int:pk>/", AdminNamingRequestDetailView.as_view(), name="admin_naming_request_detail"),
    path("admin/<int:pk>/step1/", AdminNamingRequestStep1View.as_view(), name="admin_naming_request_step1"),
    path("admin/<int:pk>/step2/", AdminNamingRequestStep2View.as_view(), name="admin_naming_request_step2"),
    path("admin/<int:pk>/step3/", AdminNamingRequestStep3View.as_view(), name="admin_naming_request_step3"),
    path("admin/<int:pk>/step4/", AdminNamingRequestStep4View.as_view(), name="admin_naming_request_step4"),
]

