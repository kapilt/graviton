
from oslo.config import cfg

from nova.openstack.common import log as logging

from nova.virt import driver as virt_driver
from nova.virt import firewall

import client

LOG = logging.getLogger(__name__)


opts = [
    cfg.IntOpt('api_version',
               default=1,
               help='Version of MAAS API service endpoint.'),
    cfg.StrOpt('api_endpoint',
               help='URL for MAAS endpoint.'),
    cfg.StrOpt('api_token',
               help='MAAS api credential token'),
    ]


graviton_group = cfg.OptGroup(name='graviton', title='Graviton Options')


CONF = cfg.CONF
CONF.register_group(graviton_group)
CONF.register_opts(opts, graviton_group)

_FIREWALL_DRIVER = "%s.%s" % (firewall.__name__,
                              firewall.NoopFirewallDriver.__name__)


class GravitonDriver(virt_driver.ComputeDriver):

    def __init__(self, virtapi, read_only=False):
        super(GravitonDriver, self).__init__(virtapi)
        self.firewall_driver = firewall.load_driver(default=_FIREWALL_DRIVER)

    def init_host(self, host):
        """Initialize anything that is necessary for the driver to function.

        :param host: the hostname of the compute host.
        """
        return

    def get_hypervisor_type(self):
        return 'maas'

    def get_hypervisor_version(self):
        return CONF.graviton.api_version

    def instance_exists(self, instance):
        """Checks the existence of an instance.

        Checks the existence of an instance. This is an override of the
        base method for efficiency.

        :param instance: The instance object.
        :returns: True if the instance exists. False if not.
        """
        return bool(client.Maas().node_get(instance['uuid']))

    def list_instances(self):
        """Return the names of all the instances provisioned.

        :returns: a list of instance names.

        """
        return [m.system_id for m in
                client.Maas().nodes(state=client.MAAS_STATES.ALLOCATED)]

    def list_instance_uuids(self):
        """Return the names of all the instances provisioned.

        :returns: a list of instance uuids.
        """
        return [m.system_id for m in
                client.Maas().nodes(state=client.MAAS_STATES.ALLOCATED)]

    def node_is_available(self, nodename):
        """Confirms a Nova hypervisor node exists in the MAAS inventory.

        :param nodename: The UUID of the node.
        :returns: True if the node exists, False if not.
        """
        return bool(client.Maas().node_get(nodename))

    def get_available_nodes(self, refresh=False):
        """Returns the UUIDs of all nodes in the MAAS inventory.

        :param refresh: Boolean value; If True run update first. Ignored by
            this driver.
        :returns: a list of UUIDs

        """
        return client.Maas().nodes()

    def get_available_resource(self, nodename):
        """Retrieve resource information.

        This method is called when nova-compute launches, and
        as part of a periodic task that records the results in the DB.

        :param nodename: the UUID of the node.
        :returns: a dictionary describing resources.
        """

    def get_info(self, instance):
        """Get the current state and resource usage for this instance.

        If the instance is not found this method returns (a dictionary
        with) NOSTATE and all resources == 0.

        :param instance: the instance object.
        :returns: a dictionary containing:
            :state: the running state. One of :mod:`nova.compute.power_state`.
            :max_mem:  (int) the maximum memory in KBytes allowed.
            :mem:      (int) the memory in KBytes used by the domain.
            :num_cpu:  (int) the number of CPUs.
            :cpu_time: (int) the CPU time used in nanoseconds. Always 0 for
                             this driver.

        """
        machine = client.Maas().node_get(instance['uuid'])
        return {'state': '',
                'max_mem': machine.mem * 1024,
                'mem': machine.mem * 1024,
                'num_cpu': machine.cpu_cores,
                'cpu_time': 0}

    def macs_for_instance(self, instance):
        """List the MAC addresses of an instance.

        List of MAC addresses for the node which this instance is
        associated with.

        :param instance: the instance object.
        :returns: a list of MAC addresses.
        """
        node = client.Maas().node_get(instance['uuid'])
        return node and set(node.mac_addresses) or None

    def spawn(self, context, instance, image_meta, injected_files,
              admin_password, network_info=None, block_device_info=None):
        """Deploy an instance.

        :param context: The security context.
        :param instance: The instance object.
        :param image_meta: Image object returned by nova.image.glance
            that defines the image from which to boot this instance.
        :param injected_files: User files to inject into instance. Ignored
            by this driver.
        :param admin_password: Administrator password to set in
            instance. Ignored by this driver.
        :param network_info: Instance network information.
        :param block_device_info: Instance block device
            information. Ignored by this driver.
        """
        maas = client.Maas()
        node = maas.node_acquire()
        if not node:
            LOG.error("Error allocating maas node")
            return
        maas.node_start(node.system_id)

    def destroy(self, context, instance, network_info,
                block_device_info=None, destroy_disks=True):
        """Destroy the specified instance, if it can be found.

        :param context: The security context.
        :param instance: The instance object.
        :param network_info: Instance network information.
        :param block_device_info: Instance block device
            information. Ignored by this driver.
        :param destroy_disks: Indicates if disks should be
            destroyed. Ignored by this driver.
        """
        maas = client.Maas()
        maas.node_stop(instance['uuid'])
        maas.node_release(instance['uuid'])

    def reboot(self, context, instance, network_info, reboot_type,
               block_device_info=None, bad_volumes_callback=None):
        """Reboot the specified instance.

        :param context: The security context.
        :param instance: The instance object.
        :param network_info: Instance network information. Ignored by
            this driver.
        :param reboot_type: Either a HARD or SOFT reboot. Ignored by
            this driver.
        :param block_device_info: Info pertaining to attached volumes.
            Ignored by this driver.
        :param bad_volumes_callback: Function to handle any bad volumes
            encountered. Ignored by this driver.

        """
        maas = client.Maas()
        maas.node_stop(instance['uuid'])
        maas.node_start(instance['uuid'])

    def power_off(self, instance):
        """Power off the specified instance.

        :param instance: The instance object.

        """
        client.Maas().node_stop(instance['uuid'])

    def power_on(self, context, instance, network_info,
                 block_device_info=None):
        """Power on the specified instance.

        :param context: The security context.
        :param instance: The instance object.
        :param network_info: Instance network information. Ignored by
            this driver.
        :param block_device_info: Instance block device
            information. Ignored by this driver.

        """
        client.Maas().node_start(instance['uuid'])

    def get_host_stats(self, refresh=False):
        """Return the currently known stats for all MAAS nodes.

        :param refresh: Boolean value; If True run update first. Ignored by
            this driver.
        :returns: a list of dictionaries; each dictionary contains the
            stats for a node.

        """

    def get_console_output(self, context, instance):
        """Get console log for an instance.

        Not Implemented Yet.

        :param context: The security context.
        :param instance: The instance object.

        """
        raise NotImplementedError()

    def refresh_security_group_rules(self, security_group_id):
        """Refresh security group rules from data store.

        Invoked when security group rules are updated.

        :param security_group_id: The security group id.

        """
        self.firewall_driver.refresh_security_group_rules(security_group_id)

    def refresh_security_group_members(self, security_group_id):
        """Refresh security group members from data store.

        Invoked when instances are added/removed to a security group.

        :param security_group_id: The security group id.

        """
        self.firewall_driver.refresh_security_group_members(security_group_id)

    def refresh_provider_fw_rules(self):
        """Triggers a firewall update based on database changes."""
        self.firewall_driver.refresh_provider_fw_rules()

    def refresh_instance_security_rules(self, instance):
        """Refresh security group rules from data store.

        Gets called when an instance gets added to or removed from
        the security group the instance is a member of or if the
        group gains or loses a rule.

        :param instance: The instance object.

        """
        self.firewall_driver.refresh_instance_security_rules(instance)

    def ensure_filtering_rules_for_instance(self, instance, network_info):
        """Set up filtering rules.

        :param instance: The instance object.
        :param network_info: Instance network information.

        """
        self.firewall_driver.setup_basic_filtering(instance, network_info)
        self.firewall_driver.prepare_instance_filter(instance, network_info)

    def unfilter_instance(self, instance, network_info):
        """Stop filtering instance.

        :param instance: The instance object.
        :param network_info: Instance network information.

        """
        self.firewall_driver.unfilter_instance(instance, network_info)

    def plug_vifs(self, instance, network_info):
        """Plug VIFs into networks.

        :param instance: The instance object.
        :param network_info: Instance network information.

        """

    def unplug_vifs(self, instance, network_info):
        """Unplug VIFs from networks.

        :param instance: The instance object.
        :param network_info: Instance network information.

        """

    def rebuild(self, context, instance, image_meta, injected_files,
                admin_password, bdms, detach_block_devices,
                attach_block_devices, network_info=None,
                recreate=False, block_device_info=None,
                preserve_ephemeral=False):
        """Rebuild/redeploy an instance.

        This version of rebuild() allows for supporting the option to
        preserve the ephemeral partition. We cannot call spawn() from
        here because it will attempt to set the instance_uuid value
        again, which is not allowed by the MAAS API. It also requires
        the instance to not have an 'active' provision state, but we
        cannot safely change that. Given that, we implement only the
        portions of spawn() we need within rebuild().

        :param context: The security context.
        :param instance: The instance object.
        :param image_meta: Image object returned by nova.image.glance
            that defines the image from which to boot this instance. Ignored
            by this driver.
        :param injected_files: User files to inject into instance. Ignored
            by this driver.
        :param admin_password: Administrator password to set in
            instance. Ignored by this driver.
        :param bdms: block-device-mappings to use for rebuild. Ignored
            by this driver.
        :param detach_block_devices: function to detach block devices. See
            nova.compute.manager.ComputeManager:_rebuild_default_impl for
            usage. Ignored by this driver.
        :param attach_block_devices: function to attach block devices. See
            nova.compute.manager.ComputeManager:_rebuild_default_impl for
            usage. Ignored by this driver.
        :param network_info: Instance network information. Ignored by
            this driver.
        :param recreate: Boolean value; if True the instance is
            recreated on a new hypervisor - all the cleanup of old state is
            skipped. Ignored by this driver.
        :param block_device_info: Instance block device
            information. Ignored by this driver.
        :param preserve_ephemeral: Boolean value; if True the ephemeral
            must be preserved on rebuild.
        """
