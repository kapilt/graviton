import logging
import requests

from requests_oauthlib import OAuth1


log = logging.getLogger(__name__)


def Maas():
    from oslo.config import cfg
    return MaasClient(cfg.CONF.graviton.api_url, cfg.CONF.graviton.api_key)


class MaasClient(object):
    """ Client Class
    """

    def __init__(self, api_url, api_key):
        """ Entry point to client routines for interfacing
        with MAAS api.

        :param auth: MAAS Authorization class (required)
        """
        self.api_url = api_url
        self.api_key = api_key
        self._client_secret = ''  # maas smells funny
        self._key, self._token, self._secret = self.api_key.split(":")

    def _oauth(self):
        """ Generates OAuth attributes for protected resources

        :returns: OAuth class
        """
        oauth = OAuth1(self._key,
                       client_secret=self._client_secret,
                       resource_owner_key=self._token,
                       resource_owner_secret=self._secret,
                       signature_method='PLAINTEXT',
                       signature_type='auth_header')
        return oauth

    def get(self, url, params=None):
        """ Performs a authenticated GET against a MAAS endpoint

        :param url: MAAS endpoint
        :param params: extra data sent with the HTTP request
        """
        return requests.get(url=self.api_url + url,
                            auth=self._oauth(),
                            params=params)

    def post(self, url, params=None):
        """ Performs a authenticated POST against a MAAS endpoint

        :param url: MAAS endpoint
        :param params: extra data sent with the HTTP request
        """
        return requests.post(url=self.api_url + url,
                             auth=self._oauth(),
                             data=params)

    def delete(self, url, params=None):
        """ Performs a authenticated DELETE against a MAAS endpoint

        :param url: MAAS endpoint
        :param params: extra data sent with the HTTP request
        """
        return requests.delete(url=self.api_url + url,
                               auth=self._oauth())

    ###########################################################################
    # APIS
    ###########################################################################
    def boot_images(self, uuid):
        """ Query boot images list

        :param str uuid: uuid of cluster
        :returns: list of boot images
        :rtype: list
        """
        res = self.get("/nodegroups/{uuid}/boot-images/".format(uuid=uuid))
        if res.ok:
            return res.json()
        return []

    @property
    def nodegroups(self):
        """ List nodegroups

        :returns: List of nodegroups
        :rtype list:
        """
        res = self.get('/nodegroups/', dict(op='list'))
        if res.ok:
            return res.json()
        return []

    @property
    def zones(self):
        """ List logical zones

        :returns: List of managed zones
        """
        res = self.get('/zones/')
        if res.ok:
            return res.json()
        return []

    @property
    def networks(self):
        """ List networks
        :returns: List of networks
        """
        res = self.get('/networks/')
        if res.ok:
            return res.json()
        return []

    ###########################################################################
    # Node API
    ###########################################################################
    def nodes(self, **params):
        """ Nodes managed by MAAS

        See http://maas.ubuntu.com/docs/api.html#nodes

        :param params: keyword parameters to filter returned nodes
                       allowed values include hostnames, mac_addresses,
                       zone.
        :returns: managed nodes
        :rtype: list
        """
        params['op'] = 'list'
        res = self.get('/nodes/', params)
        if res.ok:
            machines = map(Machine, res.json())
            # Filter by state post response manually till maas fixes.
            if 'state' in params:
                machines = [m for m in machines if m.state == params['state']]
            return machines
        return []

    def node_get(self, node_id):
        res = self.get('/nodes/%s' % node_id)
        if res.ok:
            return Machine(res.json())
        return None

    def node_acquire(self, **params):
        """
        See http://maas.ubuntu.com/docs/api.html#nodes
        """
        params['op'] = 'acquire'
        res = self.post('/nodes/', params)
        if res.ok:
            return Machine(res.json())
        return []

    def node_release(self, node_id):
        """ Release a node back into the pool.
        """
        res = self.post('/nodes/%s/' % node_id, {'op': 'release'})
        return res.ok

    def node_start(self, node_id, user_data=None, distro_series=None):
        """ Power up a node

        :param node_id: machine identification
        :returns: True on success False on failure
        """
        params = {'op': 'start'}
        if user_data:
            params['user_data'] = user_data
        if distro_series:
            params['distro_series'] = distro_series
        res = self.post('/nodes/%s/' % node_id, params)
        return res.ok

    def node_stop(self, node_id):
        """ Shutdown a node

        :param node_id: machine identification
        :returns: True on success False on failure
        """
        res = self.post('/nodes/%s/' % node_id, {'op': 'stop'})
        return res.ok


class vocab(dict):
    __slots__ = ()

    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            return AttributeError(k)

    def label(self, value):
        for k, v in self.items():
            if v == value:
                return k

MAAS_STATES = vocab(
    DECLARED=0,
    COMMISSIONING=1,
    FAILED_TESTS=2,
    MISSING=3,
    READY=4,
    RESERVED=5,
    ALLOCATED=6,
    RETIRED=7)


class Machine(dict):

    __slots__ = ()

    @property
    def hostname(self):
        return self['hostname']

    @property
    def arch(self):
        return self['architecture']

    @property
    def status(self):
        return self['status']

    @property
    def cpu_cores(self):
        return self['cpu_count']

    @property
    def mem(self):
        """ Size Memory in mb"""
        return self['memory']

    @property
    def disk(self):
        """ Size root disk in gb"""
        return self['storage']

    @property
    def system_id(self):
        return self['system_id']

    @property
    def tags(self):
        return self.get('tags', [])

    @property
    def ip_addresses(self):
        return self['ip_addresses']

    @property
    def mac_addresses(self):
        return [m['mac_address'] for m in self.get('macaddress_set', [])]

    @property
    def status_label(self):
        return MAAS_STATES.label(self.status)
