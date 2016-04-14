import json
import os
import responses

from unittest import TestCase
from urllib.parse import quote

from ukti.datahub.colossus import app
from ukti.datahub.mystique import Mystique


class BastionTestCase(TestCase):

    AUTH_SERVER = "http://localhost:5000"
    BASTION_SERVER = "http://localhost:5001"
    DATA_SERVER = "http://localhost:5002"

    BASTION_SECRET = "secret"

    def setUp(self):

        os.environ["AUTH_SERVER"] = self.AUTH_SERVER
        os.environ["BASTION_SERVER"] = self.BASTION_SERVER
        os.environ["DATA_SERVER"] = self.DATA_SERVER
        os.environ["BASTION_SECRET"] = self.BASTION_SECRET

        app.config['TESTING'] = True

        self.bastion = app.test_client()

    def test_cookie_rejection(self):

        for url in ("/", "/anything", "/anything/εłσε", "/asdf?jkl=semicolon"):
            r = self.bastion.get(url)
            self.assertEqual(r.status_code, 400, url)
            self.assertEqual(
                json.loads(r.get_data().decode("utf-8"))["message"],
                "{}/?next={}{}".format(
                    self.AUTH_SERVER,
                    quote(self.BASTION_SERVER, safe=""),
                    quote(url, safe="")
                ),
                url
            )

    @responses.activate
    def test_bad_data_response(self):

        responses.add(
            responses.GET,
            "{}/".format(self.DATA_SERVER),
            body='{"this": "is", "some": "content"}',
            status=400,
            content_type='application/json'
        )

        self.bastion.set_cookie("localhost", Mystique.COOKIE, "")
        r = self.bastion.get("/")
        self.assertEqual(r.status_code, 400)

    @responses.activate
    def test_good_data_response(self):

        session_token = ("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzZXNzaW9uIjo"
                         "ic2Vzc2lvbi1pZCJ9.WjjrK_pMyDO2nYxJ9vKD67M0kM4k0ZR7rw"
                         "a-q_rwSzY")

        responses.add(
            responses.GET,
            "{}/".format(self.DATA_SERVER),
            body='{"this": "is", "some": "content"}',
            status=200,
            adding_headers={Mystique.HEADER_NAME: session_token},
            content_type='application/json'
        )

        self.bastion.set_cookie("localhost", Mystique.COOKIE, "irrelevant")
        r = self.bastion.get("/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.get_data().decode("utf-8"))
        self.assertEqual(data["this"], "is")
        self.assertEqual(data["some"], "content")
        print(r.headers["Set-Cookie"])
        self.assertEqual(
            r.headers["Set-Cookie"].split(";")[0].split("=")[1],
            session_token
        )
