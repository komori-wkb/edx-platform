import factory
from factory.django import DjangoModelFactory
from certificates.models import CertificateWhitelist, GeneratedCertificate
from opaque_keys.edx.locator import CourseLocator
from student.tests.factories import UserFactory
from datetime import datetime
from pytz import UTC


class CertificateWhitelistFactory(DjangoModelFactory):
    class Meta(object):
        model = CertificateWhitelist

    user = factory.SubFactory(UserFactory)
    course_id = CourseLocator.from_string("org/num/run")
    whitelist = True


class GeneratedCertificateFactory(DjangoModelFactory):
    class Meta(object):
        model = GeneratedCertificate

    user = factory.SubFactory(UserFactory)
    course_id = CourseLocator.from_string("org/num/run")
    verify_uuid = ''
    download_uuid = ''
    download_url = "http://example.com/"
    grade = 1.0
    key = "012345678901234567890123456789ab"
    distinction = False
    status = "downloadable"
    #mode = 'honor'
    mode = GeneratedCertificate.MODES.honor
    name = "testuser"
    created_date = datetime.now(UTC)
    modified_date = datetime.now(UTC)
    error_reason = "error reason"
    """
    status = "unavailable"
    mode = factory.Iterator(['verified', 'honor', 'audit'])

    def save():
        pass
    """


"""
username = factory.Sequence(lambda n: "user_%d" % n)
name = factory.Iterator(["France", "Italy", "Spain"])
email = factory.LazyAttribute(lambda o: '%s@example.com' % o.username
email = factory.LazyAttributeSequence(
    lambda o, n: '%s@s%d.example.com' % (o.login, n))
birthdate = factory.Sequence(
    lambda n: datetime.date(2000, 1, 1) + datetime.timedelta(days=n))
birthmonth = factory.SelfAttribute('birthdate.month')
 name?

 fuszzy? FuzzyChoice
    build provides a local object
    create instantiates a local object, and saves it to the database.

"""
