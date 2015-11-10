"""Tests for account creation"""
from datetime import datetime
import json
import unittest

import ddt
from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.core.urlresolvers import reverse
from django.test import TestCase, TransactionTestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.utils.importlib import import_module
import mock

from openedx.core.djangoapps.user_api.preferences.api import get_user_preference
from lang_pref import LANGUAGE_KEY
from notification_prefs import NOTIFICATION_PREF_KEY
from edxmako.tests import mako_middleware_process_request
from external_auth.models import ExternalAuthMap

from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory
from openedx.core.djangoapps.course_global.tests.factories import CourseGlobalSettingFactory

from opaque_keys.edx.locations import SlashSeparatedCourseKey

import student

TEST_CS_URL = 'https://comments.service.test:123/'


@ddt.ddt
@override_settings(
    MICROSITE_CONFIGURATION={
        "microsite": {
            "domain_prefix": "microsite",
            "extended_profile_fields": ["extra1", "extra2"],
        }
    },
    REGISTRATION_EXTRA_FIELDS={
        key: "optional"
        for key in [
            "level_of_education", "gender", "mailing_address", "city", "country", "goals",
            "year_of_birth"
        ]
    }
)
class TestCreateAccount(ModuleStoreTestCase):
    """Tests for account creation"""

    def setUp(self):
        super(TestCreateAccount, self).setUp(**{'create_user': False})

        self.username = "test_user"
        self.url = reverse("create_account")
        self.request_factory = RequestFactory()
        self.params = {
            "username": self.username,
            "email": "test@example.org",
            "password": "testpass",
            "name": "Test User",
            "honor_code": "true",
            "terms_of_service": "true",
        }
        self.course_1 = CourseFactory.create(display_name="test course 1")
        self.course_2 = CourseFactory.create(display_name="test course 2")

    @ddt.data("en", "eo")
    def test_default_lang_pref_saved(self, lang):
        with mock.patch("django.conf.settings.LANGUAGE_CODE", lang):
            response = self.client.post(self.url, self.params)
            self.assertEqual(response.status_code, 200)
            user = User.objects.get(username=self.username)
            self.assertEqual(get_user_preference(user, LANGUAGE_KEY), lang)

    @ddt.data("en", "eo")
    def test_header_lang_pref_saved(self, lang):
        response = self.client.post(self.url, self.params, HTTP_ACCEPT_LANGUAGE=lang)
        user = User.objects.get(username=self.username)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_preference(user, LANGUAGE_KEY), lang)

    def create_account_and_fetch_profile(self):
        """
        Create an account with self.params, assert that the response indicates
        success, and return the UserProfile object for the newly created user
        """
        response = self.client.post(self.url, self.params, HTTP_HOST="microsite.example.com")
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username=self.username)
        return user.profile

    def test_marketing_cookie(self):
        response = self.client.post(self.url, self.params)
        self.assertEqual(response.status_code, 200)
        self.assertIn(settings.EDXMKTG_LOGGED_IN_COOKIE_NAME, self.client.cookies)
        self.assertIn(settings.EDXMKTG_USER_INFO_COOKIE_NAME, self.client.cookies)

    @unittest.skipUnless(
        "microsite_configuration.middleware.MicrositeMiddleware" in settings.MIDDLEWARE_CLASSES,
        "Microsites not implemented in this environment"
    )
    def test_profile_saved_no_optional_fields(self):
        profile = self.create_account_and_fetch_profile()
        self.assertEqual(profile.name, self.params["name"])
        self.assertEqual(profile.level_of_education, "")
        self.assertEqual(profile.gender, "")
        self.assertEqual(profile.mailing_address, "")
        self.assertEqual(profile.city, "")
        self.assertEqual(profile.country, "")
        self.assertEqual(profile.goals, "")
        self.assertEqual(
            profile.get_meta(),
            {
                "extra1": "",
                "extra2": "",
            }
        )
        self.assertIsNone(profile.year_of_birth)

    @unittest.skipUnless(
        "microsite_configuration.middleware.MicrositeMiddleware" in settings.MIDDLEWARE_CLASSES,
        "Microsites not implemented in this environment"
    )
    @override_settings(LMS_SEGMENT_KEY="testkey")
    @mock.patch('student.views.analytics.track')
    @mock.patch('student.views.analytics.identify')
    def test_segment_tracking(self, mock_segment_identify, _):
        year = datetime.now().year
        self.params.update({
            "level_of_education": "a",
            "gender": "o",
            "mailing_address": "123 Example Rd",
            "city": "Exampleton",
            "country": "US",
            "goals": "To test this feature",
            "year_of_birth": str(year),
            "extra1": "extra_value1",
            "extra2": "extra_value2",
        })

        expected_payload = {
            'email': self.params['email'],
            'username': self.params['username'],
            'name': self.params['name'],
            'age': 0,
            'education': 'Associate degree',
            'address': self.params['mailing_address'],
            'gender': 'Other/Prefer Not to Say',
            'country': self.params['country'],
        }

        self.create_account_and_fetch_profile()

        mock_segment_identify.assert_called_with(1, expected_payload)

    @unittest.skipUnless(
        "microsite_configuration.middleware.MicrositeMiddleware" in settings.MIDDLEWARE_CLASSES,
        "Microsites not implemented in this environment"
    )
    def test_profile_saved_all_optional_fields(self):
        self.params.update({
            "level_of_education": "a",
            "gender": "o",
            "mailing_address": "123 Example Rd",
            "city": "Exampleton",
            "country": "US",
            "goals": "To test this feature",
            "year_of_birth": "2015",
            "extra1": "extra_value1",
            "extra2": "extra_value2",
        })
        profile = self.create_account_and_fetch_profile()
        self.assertEqual(profile.level_of_education, "a")
        self.assertEqual(profile.gender, "o")
        self.assertEqual(profile.mailing_address, "123 Example Rd")
        self.assertEqual(profile.city, "Exampleton")
        self.assertEqual(profile.country, "US")
        self.assertEqual(profile.goals, "To test this feature")
        self.assertEqual(
            profile.get_meta(),
            {
                "extra1": "extra_value1",
                "extra2": "extra_value2",
            }
        )
        self.assertEqual(profile.year_of_birth, 2015)

    @unittest.skipUnless(
        "microsite_configuration.middleware.MicrositeMiddleware" in settings.MIDDLEWARE_CLASSES,
        "Microsites not implemented in this environment"
    )
    def test_profile_saved_empty_optional_fields(self):
        self.params.update({
            "level_of_education": "",
            "gender": "",
            "mailing_address": "",
            "city": "",
            "country": "",
            "goals": "",
            "year_of_birth": "",
            "extra1": "",
            "extra2": "",
        })
        profile = self.create_account_and_fetch_profile()
        self.assertEqual(profile.level_of_education, "")
        self.assertEqual(profile.gender, "")
        self.assertEqual(profile.mailing_address, "")
        self.assertEqual(profile.city, "")
        self.assertEqual(profile.country, "")
        self.assertEqual(profile.goals, "")
        self.assertEqual(
            profile.get_meta(),
            {"extra1": "", "extra2": ""}
        )
        self.assertEqual(profile.year_of_birth, None)

    def test_profile_year_of_birth_non_integer(self):
        self.params["year_of_birth"] = "not_an_integer"
        profile = self.create_account_and_fetch_profile()
        self.assertIsNone(profile.year_of_birth)

    def base_extauth_bypass_sending_activation_email(self, bypass_activation_email):
        """
        Tests user creation without sending activation email when
        doing external auth
        """

        request = self.request_factory.post(self.url, self.params)
        # now indicate we are doing ext_auth by setting 'ExternalAuthMap' in the session.
        request.session = import_module(settings.SESSION_ENGINE).SessionStore()  # empty session
        extauth = ExternalAuthMap(external_id='withmap@stanford.edu',
                                  external_email='withmap@stanford.edu',
                                  internal_password=self.params['password'],
                                  external_domain='shib:https://idp.stanford.edu/')
        request.session['ExternalAuthMap'] = extauth
        request.user = AnonymousUser()

        mako_middleware_process_request(request)
        with mock.patch('django.contrib.auth.models.User.email_user') as mock_send_mail:
            student.views.create_account(request)

        # check that send_mail is called
        if bypass_activation_email:
            self.assertFalse(mock_send_mail.called)
        else:
            self.assertTrue(mock_send_mail.called)

    @unittest.skipUnless(settings.FEATURES.get('AUTH_USE_SHIB'), "AUTH_USE_SHIB not set")
    @mock.patch.dict(settings.FEATURES, {'BYPASS_ACTIVATION_EMAIL_FOR_EXTAUTH': True, 'AUTOMATIC_AUTH_FOR_TESTING': False})
    def test_extauth_bypass_sending_activation_email_with_bypass(self):
        """
        Tests user creation without sending activation email when
        settings.FEATURES['BYPASS_ACTIVATION_EMAIL_FOR_EXTAUTH']=True and doing external auth
        """
        self.base_extauth_bypass_sending_activation_email(True)

    @unittest.skipUnless(settings.FEATURES.get('AUTH_USE_SHIB'), "AUTH_USE_SHIB not set")
    @mock.patch.dict(settings.FEATURES, {'BYPASS_ACTIVATION_EMAIL_FOR_EXTAUTH': False, 'AUTOMATIC_AUTH_FOR_TESTING': False})
    def test_extauth_bypass_sending_activation_email_without_bypass(self):
        """
        Tests user creation without sending activation email when
        settings.FEATURES['BYPASS_ACTIVATION_EMAIL_FOR_EXTAUTH']=False and doing external auth
        """
        self.base_extauth_bypass_sending_activation_email(False)

    @unittest.skipUnless(settings.FEATURES.get('AUTH_USE_SHIB'), "AUTH_USE_SHIB not set")
    @mock.patch.dict(settings.FEATURES, {'BYPASS_ACTIVATION_EMAIL_FOR_EXTAUTH': False, 'AUTOMATIC_AUTH_FOR_TESTING': False, 'SKIP_EMAIL_VALIDATION': True})
    def test_extauth_bypass_sending_activation_email_without_bypass(self):
        """
        Tests user creation without sending activation email when
        settings.FEATURES['BYPASS_ACTIVATION_EMAIL_FOR_EXTAUTH']=False and doing external auth
        """
        self.base_extauth_bypass_sending_activation_email(True)

    @ddt.data(True, False)
    def test_discussions_email_digest_pref(self, digest_enabled):
        with mock.patch.dict("student.models.settings.FEATURES", {"ENABLE_DISCUSSION_EMAIL_DIGEST": digest_enabled}):
            response = self.client.post(self.url, self.params)
            self.assertEqual(response.status_code, 200)
            user = User.objects.get(username=self.username)
            preference = get_user_preference(user, NOTIFICATION_PREF_KEY)
            if digest_enabled:
                self.assertIsNotNone(preference)
            else:
                self.assertIsNone(preference)

    @unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
    def test_no_global_course(self):
        response = self.client.post(self.url, self.params)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username=self.username)
        self.assertEqual(0, student.models.CourseEnrollmentAllowed.objects.all().count())

    @unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
    def test_exists_global_course(self):
        dummy_course_id = SlashSeparatedCourseKey('a', 'b', 'c')
        CourseGlobalSettingFactory.create(course_id=dummy_course_id)
        CourseGlobalSettingFactory.create(course_id=self.course_1.id)
        CourseGlobalSettingFactory.create(course_id=self.course_2.id)

        response = self.client.post(self.url, self.params)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username=self.username)
        cea1 = student.models.CourseEnrollmentAllowed.objects.get(email=user.email, course_id=self.course_1.id)
        self.assertTrue(cea1.auto_enroll)
        cea2 = student.models.CourseEnrollmentAllowed.objects.get(email=user.email, course_id=self.course_2.id)
        self.assertTrue(cea2.auto_enroll)
        self.assertFalse(student.models.CourseEnrollmentAllowed.objects.filter(course_id=dummy_course_id))


@ddt.ddt
class TestCreateAccountValidation(TestCase):
    """
    Test validation of various parameters in the create_account view
    """
    def setUp(self):
        super(TestCreateAccountValidation, self).setUp()
        self.url = reverse("create_account")
        self.minimal_params = {
            "username": "test_username",
            "email": "test_email@example.com",
            "password": "test_password",
            "name": "Test Name",
            "honor_code": "true",
            "terms_of_service": "true",
        }

    def assert_success(self, params):
        """
        Request account creation with the given params and assert that the
        response properly indicates success
        """
        response = self.client.post(self.url, params)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])

    def assert_error(self, params, expected_field, expected_value):
        """
        Request account creation with the given params and assert that the
        response properly indicates an error with the given field and value
        """
        response = self.client.post(self.url, params)
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data["success"])
        self.assertEqual(response_data["field"], expected_field)
        self.assertEqual(response_data["value"], expected_value)

    def test_minimal_success(self):
        self.assert_success(self.minimal_params)

    def test_username(self):
        params = dict(self.minimal_params)

        def assert_username_error(expected_error):
            """
            Assert that requesting account creation results in the expected
            error
            """
            self.assert_error(params, "username", expected_error)

        # Missing
        del params["username"]
        assert_username_error("Username must be minimum of two characters long")

        # Empty, too short
        for username in ["", "a"]:
            params["username"] = username
            assert_username_error("Username must be minimum of two characters long")

        # Too long
        params["username"] = "this_username_has_31_characters"
        assert_username_error("Username cannot be more than 30 characters long")

        # Invalid
        params["username"] = "invalid username"
        assert_username_error("Usernames must contain only letters, numbers, underscores (_), and hyphens (-).")

    def test_email(self):
        params = dict(self.minimal_params)

        def assert_email_error(expected_error):
            """
            Assert that requesting account creation results in the expected
            error
            """
            self.assert_error(params, "email", expected_error)

        # Missing
        del params["email"]
        assert_email_error("A properly formatted e-mail is required")

        # Empty, too short
        for email in ["", "a"]:
            params["email"] = email
            assert_email_error("A properly formatted e-mail is required")

        # Too long
        params["email"] = "this_email_address_has_76_characters_in_it_so_it_is_unacceptable@example.com"
        assert_email_error("Email cannot be more than 75 characters long")

        # Invalid
        params["email"] = "not_an_email_address"
        assert_email_error("A properly formatted e-mail is required")

    def test_password(self):
        params = dict(self.minimal_params)

        def assert_password_error(expected_error):
            """
            Assert that requesting account creation results in the expected
            error
            """
            self.assert_error(params, "password", expected_error)

        # Missing
        del params["password"]
        assert_password_error("A valid password is required")

        # Empty, too short
        for password in ["", "a"]:
            params["password"] = password
            assert_password_error("A valid password is required")

        # Password policy is tested elsewhere

        # Matching username
        params["username"] = params["password"] = "test_username_and_password"
        assert_password_error("Username and password fields cannot match")

    def test_name(self):
        params = dict(self.minimal_params)

        def assert_name_error(expected_error):
            """
            Assert that requesting account creation results in the expected
            error
            """
            self.assert_error(params, "name", expected_error)

        # Missing
        del params["name"]
        assert_name_error("Your legal name must be a minimum of two characters long")

        # Empty, too short
        for name in ["", "a"]:
            params["name"] = name
            assert_name_error("Your legal name must be a minimum of two characters long")

    def test_honor_code(self):
        params = dict(self.minimal_params)

        def assert_honor_code_error(expected_error):
            """
            Assert that requesting account creation results in the expected
            error
            """
            self.assert_error(params, "honor_code", expected_error)

        with override_settings(REGISTRATION_EXTRA_FIELDS={"honor_code": "required"}):
            # Missing
            del params["honor_code"]
            assert_honor_code_error("To enroll, you must follow the honor code.")

            # Empty, invalid
            for honor_code in ["", "false", "not_boolean"]:
                params["honor_code"] = honor_code
                assert_honor_code_error("To enroll, you must follow the honor code.")

            # True
            params["honor_code"] = "tRUe"
            self.assert_success(params)

        with override_settings(REGISTRATION_EXTRA_FIELDS={"honor_code": "optional"}):
            # Missing
            del params["honor_code"]
            # Need to change username/email because user was created above
            params["username"] = "another_test_username"
            params["email"] = "another_test_email@example.com"
            self.assert_success(params)

    def test_terms_of_service(self):
        params = dict(self.minimal_params)

        def assert_terms_of_service_error(expected_error):
            """
            Assert that requesting account creation results in the expected
            error
            """
            self.assert_error(params, "terms_of_service", expected_error)

        # Missing
        del params["terms_of_service"]
        assert_terms_of_service_error("You must accept the terms of service.")

        # Empty, invalid
        for terms_of_service in ["", "false", "not_boolean"]:
            params["terms_of_service"] = terms_of_service
            assert_terms_of_service_error("You must accept the terms of service.")

        # True
        params["terms_of_service"] = "tRUe"
        self.assert_success(params)

    @ddt.data(
        ("level_of_education", 1, "A level of education is required"),
        ("gender", 1, "Your gender is required"),
        ("year_of_birth", 2, "Your year of birth is required"),
        ("mailing_address", 2, "Your mailing address is required"),
        ("goals", 2, "A description of your goals is required"),
        ("city", 2, "A city is required"),
        ("country", 2, "A country is required"),
        ("custom_field", 2, "You are missing one or more required fields")
    )
    @ddt.unpack
    def test_extra_fields(self, field, min_length, expected_error):
        params = dict(self.minimal_params)

        def assert_extra_field_error():
            """
            Assert that requesting account creation results in the expected
            error
            """
            self.assert_error(params, field, expected_error)

        with override_settings(REGISTRATION_EXTRA_FIELDS={field: "required"}):
            # Missing
            assert_extra_field_error()

            # Empty
            params[field] = ""
            assert_extra_field_error()

            # Too short
            if min_length > 1:
                params[field] = "a"
                assert_extra_field_error()


@mock.patch.dict("student.models.settings.FEATURES", {"ENABLE_DISCUSSION_SERVICE": True})
@mock.patch("lms.lib.comment_client.User.base_url", TEST_CS_URL)
@mock.patch("lms.lib.comment_client.utils.requests.request", return_value=mock.Mock(status_code=200, text='{}'))
class TestCreateCommentsServiceUser(TransactionTestCase):

    def setUp(self):
        super(TestCreateCommentsServiceUser, self).setUp()
        self.username = "test_user"
        self.url = reverse("create_account")
        self.params = {
            "username": self.username,
            "email": "test@example.org",
            "password": "testpass",
            "name": "Test User",
            "honor_code": "true",
            "terms_of_service": "true",
        }

    def test_cs_user_created(self, request):
        "If user account creation succeeds, we should create a comments service user"
        response = self.client.post(self.url, self.params)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(request.called)
        args, kwargs = request.call_args
        self.assertEqual(args[0], 'put')
        self.assertTrue(args[1].startswith(TEST_CS_URL))
        self.assertEqual(kwargs['data']['username'], self.params['username'])

    @mock.patch("student.models.Registration.register", side_effect=Exception)
    def test_cs_user_not_created(self, register, request):
        "If user account creation fails, we should not create a comments service user"
        try:
            response = self.client.post(self.url, self.params)
        except:
            pass
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(username=self.username)
        self.assertTrue(register.called)
        self.assertFalse(request.called)
