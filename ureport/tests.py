from dash.api import API
from smartmin.tests import SmartminTest
from django.contrib.auth.models import User, Group
from dash.orgs.middleware import SetOrgMiddleware
from mock import Mock
from django.core.urlresolvers import reverse
from dash.orgs.models import Org
from django.http.request import HttpRequest

class MockAPI(API):

    def get_group(self, name):
        return dict(group=8, name=name, size=120)

    def get_country_geojson(self):
        return dict(
                   type="FeatureCollection",
                   features=[
                       dict(
                           type='Feature',
                           properties=dict(
                               id="R3713501",
                               level=1,
                               name="Abia"
                           ),
                           geometry=dict(
                               type="MultiPolygon",
                               coordinates=[
                                   [
                                       [
                                           [7, 5]
                                       ]
                                   ]
                               ]
                           )
                       )
                   ]
            )

    def get_state_geojson(self, state_id):
        return dict(type="FeatureCollection",
                    features=[dict(type='Feature',
                                   properties=dict(id="R3713502",
                                                   level=2,
                                                   name="Aba North"),
                                   geometry=dict(type="MultiPolygon",
                                                 coordinates=[[[[8, 4]]]]
                                                 )
                                   )
                            ]
                    )

    def get_ruleset_results(self, ruleset_id, segment=None):
        return [dict(open_ended=False,
                     set=3462,
                     unset=3694,
                     categories=[dict(count=2210,
                                      label='Yes'
                                      ),
                                 dict(count=1252,
                                      label='No'
                                      )
                                 ],
                     label='All')
                ]

    def get_contact_field_results(self, contact_field_label, segment=None):
        return [
            dict(
                open_ended=False,
                set=3462,
                unset=3694,
                categories=[
                    dict(
                        count=2210,
                        label='Yes'
                    ),
                    dict(
                        count=1252,
                        label='No'
                    )
                ],
                label='All'
            )
        ]

    def get_flows(self, filter=None):
        return [
            dict(
                runs=300,
                completed_runs=120,
                name='Flow 1',
                flow='25',
                participants=300,
                rulesets=[
                   dict(node='386fc244-cc98-476a-b05e-f8a431a4dd41',
                        id=8435,
                        label='Does your community have power'
                   )
                ]

            )
        ]

class DashTest(SmartminTest):

    def setUp(self):
        self.superuser = User.objects.create_superuser(username="super", email="super@user.com", password="super")

        self.admin = self.create_user("Administrator")

    def create_org(self, subdomain, user):

        email = subdomain + "@user.com"
        first_name = subdomain + "_First"
        last_name = subdomain + "_Last"
        name = subdomain

        orgs = Org.objects.filter(subdomain=subdomain)
        if orgs:
            org =orgs[0]
            org.name = name
            org.save()
        else:
            org = Org.objects.create(subdomain=subdomain, name=name, created_by=user, modified_by=user)

        org.administrators.add(user)

        self.assertEquals(Org.objects.filter(subdomain=subdomain).count(), 1)
        return Org.objects.get(subdomain=subdomain)


class SetOrgMiddlewareTest(DashTest):

    def setUp(self):
        super(SetOrgMiddlewareTest, self).setUp()

        self.middleware = SetOrgMiddleware()
        self.request = Mock(spec=HttpRequest)
        self.request.user = User.objects.get(pk=-1)
        self.request.path = '/'
        self.request.get_host.return_value="ureport.io"
        self.request.META = dict(HTTP_HOST=None)

    def test_process_request_without_org(self):
        response = self.middleware.process_request(self.request)
        self.assertEqual(response.template_name, 'public/org_chooser.haml')
        self.assertFalse(response.context_data['orgs'])

    def test_process_request_with_org(self):

        ug_org = self.create_org('uganda', self.admin)
        ug_dash_url = ug_org.subdomain + ".ureport.io"
        self.request.get_host.return_value=ug_dash_url

        response = self.middleware.process_request(self.request)
        self.assertEqual(response, None)
        self.assertEqual(self.request.org, ug_org)

        self.request.user = self.admin
        response = self.middleware.process_request(self.request)
        self.assertEqual(response, None)
        self.assertEqual(self.request.org, ug_org)
        self.assertEquals(self.request.user.get_org(), ug_org)

        # test invalid subdomain
        wrong_subdomain_url = "blabla.ureport.io"
        self.request.get_host.return_value=wrong_subdomain_url
        response = self.middleware.process_request(self.request)
        self.assertEqual(response.template_name, 'public/org_chooser.haml')
        self.assertEquals(len(response.context_data['orgs']), 1)
        self.assertEquals(response.context_data['orgs'][0], ug_org)
        self.assertEqual(self.request.org, None)
        self.assertEquals(self.request.user.get_org(), None)

        rw_org = self.create_org('rwanda', self.admin)
        wrong_subdomain_url = "blabla.ureport.io"
        self.request.get_host.return_value=wrong_subdomain_url
        response = self.middleware.process_request(self.request)
        self.assertEqual(response.template_name, 'public/org_chooser.haml')
        self.assertEquals(len(response.context_data['orgs']), 2)
        self.assertTrue(rw_org in response.context_data['orgs'])
        self.assertTrue(ug_org in response.context_data['orgs'])
