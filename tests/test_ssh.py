#!/usr/bin/env python3
#
# Copyright 2021 Venafi, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging
import unittest

from test_env import timestamp, TPP_TOKEN_URL, TPP_USER, TPP_PASSWORD, SSH_CADN
from vcert import CommonConnection, SSHCertRequest, TPPTokenConnection, Authentication, \
    SCOPE_SSH, generate_ssh_keypair
from vcert.ssh_utils import SSHRetrieveResponse

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('vcert-test')


SERVICE_GENERATED_NO_KEY_ERROR = "%s key data is %s empty for Certificate %s"  # type: str
SSH_CERT_DATA_ERROR = "Certificate data is empty for Certificate %s"  # type: str


class TestTPPSSHCertificate(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.tpp_conn = TPPTokenConnection(url=TPP_TOKEN_URL, http_request_kwargs={"verify": "/tmp/chain.pem"})
        auth = Authentication(user=TPP_USER, password=TPP_PASSWORD, scope=SCOPE_SSH)
        self.tpp_conn.get_access_token(auth)
        super(TestTPPSSHCertificate, self).__init__(*args, **kwargs)

    def test_enroll_local_generated_keypair(self):
        keypair = generate_ssh_keypair(key_size=4096, passphrase="foobar")

        request = SSHCertRequest(cadn=SSH_CADN, key_id=_random_key_id())
        request.validity_period = "4h"
        request.source_addresses = ["test.com"]
        request.set_public_key_data(keypair.public_key)
        response = _enroll_ssh_cert(self.tpp_conn, request)
        self.assertTrue(response.private_key_data is None,
                        SERVICE_GENERATED_NO_KEY_ERROR % ("Private", "not", request.key_id))
        self.assertTrue(response.public_key_data, SERVICE_GENERATED_NO_KEY_ERROR % ("Public", "", request.key_id))
        self.assertTrue(response.public_key_data == request.get_public_key_data(),
                        "Public key on response does not match request.\nExpected: %s\nGot: %s"
                        % (request.get_public_key_data(), response.public_key_data))
        self.assertTrue(response.cert_data, SSH_CERT_DATA_ERROR % request.key_id)

    def test_enroll_service_generated_keypair(self):
        request = SSHCertRequest(cadn=SSH_CADN, key_id=_random_key_id())
        request.validity_period = "4h"
        request.source_addresses = ["test.com"]
        response = _enroll_ssh_cert(self.tpp_conn, request)
        self.assertTrue(response.private_key_data, SERVICE_GENERATED_NO_KEY_ERROR % ("Private", "", request.key_id))
        self.assertTrue(response.public_key_data, SERVICE_GENERATED_NO_KEY_ERROR % ("Public", "", request.key_id))
        self.assertTrue(response.cert_data, SSH_CERT_DATA_ERROR % request.key_id)


def _enroll_ssh_cert(connector, request):
    """
    :param CommonConnection connector:
    :param SSHCertRequest request:
    :rtype: SSHRetrieveResponse
    """
    success = connector.request_ssh_cert(request)
    assert success
    response = connector.retrieve_ssh_cert(request)
    assert isinstance(response, SSHRetrieveResponse)
    return response


def _random_key_id():
    return "vcert-python-ssh-%s" % timestamp()
