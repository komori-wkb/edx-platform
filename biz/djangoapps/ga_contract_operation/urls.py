"""
URLconf for contract_operation views
"""
from django.conf.urls import patterns, url

urlpatterns = patterns(
    'biz.djangoapps.ga_contract_operation.views',

    url(r'^students$', 'students', name='students'),
    url(r'^register_students$', 'register_students', name='register_students'),
    url(r'^register_students_ajax$', 'register_students_ajax', name='register_students_ajax'),
)
