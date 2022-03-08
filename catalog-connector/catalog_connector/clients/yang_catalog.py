import logging
from enum import Enum

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

YANG_CATALOG_URL = "https://yangcatalog.org/api"

logger = logging.getLogger(__name__)


class YangCatalogAPI:
    def __init__(
        self,
        url: str = YANG_CATALOG_URL,
        headers: dict = {"Accept": "application/json"},
        disable_ssl: bool = False,
        debug: bool = False,
    ):

        self.headers = headers
        self.url = url
        self.ssl_verification = not disable_ssl
        # Retry strategy
        retry_strategy = Retry(
            total=10,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "PUT", "POST", "OPTIONS"],
            backoff_factor=5,
        )
        self._session = requests.Session()
        self._session.mount(self.url, HTTPAdapter(max_retries=retry_strategy))
        self.debug = debug
        if self.debug:
            import http.client as http_client
            import logging

            http_client.HTTPConnection.debuglevel = 1

            # You must initialize logging,
            # otherwise you'll not see debug output.
            logging.basicConfig()
            logging.getLogger().setLevel(logging.DEBUG)
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.propagate = True

    def get_whole_catalog(self):
        """
        This endpoint serves to get all the modules with
        their vendor implementation metadata
        """
        response = self._session.get(
            "{0}/search/catalog".format(self.url),
            verify=self.ssl_verification,
            headers=self.headers,
        )
        return response.json()

    def get_all_modules_metadata(self):
        """
        This endpoint serves to get all the modules metadata
        """
        response = self._session.get(
            "{0}/search/modules".format(self.url),
            verify=self.ssl_verification,
            headers=self.headers,
        )
        return response.json()

    def filter_leaf_data(self, path_value):
        """
        This endpoint serves to get all the modules that
        correspond with provided keyword
        :param path_value:	Path to a specific vendor modules you want to remove
                            (example: cisco/xe/1632 would delete
                            all 1632 xe cisco modules)
        """
        response = self._session.get(
            "{0}/search/{1}".format(self.url, path_value),
            verify=self.ssl_verification,
            headers=self.headers,
        )
        return response.json()
