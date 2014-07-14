Graviton
========

Graviton is an openstack nova virtualization driver which aims to
provision bare metal machines instead of virtual machines via using
the MAAS provisioning sytem http://maas.ubuntu.com

**Work in progress**


Todo
----

 - image mapping glance to maas
   - per cc image set
   - map logical image to set of maas images
   - utilize metadata on image?
   - simplify and handle of out band?
 - vif/port plugin
 - check if maas supports stop/start without reinstall
 - cloudinit / userdata from md server vs maas ?
 - instance id storage (use maas id, k/v tag)



-----------------
Project Resources
-----------------

Project status, bugs, and blueprints are tracked on Launchpad:

  http://github.com/kapilt/graviton

Developer documentation can be found here:

  http://github.com/kapilt/graviton/docs

Anyone wishing to contribute to an OpenStack project should
find plenty of helpful resources here:

  https://wiki.openstack.org/wiki/HowToContribute

All OpenStack projects use Gerrit for code reviews.
A good reference for that is here:

  https://wiki.openstack.org/wiki/GerritWorkflow
