====================
Example Bay Template
====================

This project is an example to demonstrate the necessary pieces of a Bay
template. There are three key pieces to a bay template:

1. Heat template - The Heat template that Magnum will use to generate a Bay.
2. Template definition - Magnum's interface for interacting with the Heat
   template.
3. Definition Entry Point - Used to advertise the available template
   definitions.

The Heat Template
-----------------

The heat template is where most of the real work happens. The result of the
Heat template should be a full Container Orchestration Environment.

The Template Definition
-----------------------

Template definitions are a mapping of Magnum object attributes and Heat
template parameters, along with Magnum consumable template outputs. Each
definition also denotes which Bay Types it can provide. Bay Types are how
Magnum determines which of the enabled Template Definitions it will use for a
given Bay.

The Definition Entry Point
--------------------------

Entry points are a standard discovery and import mechanism for Python objects.
Each Template Definition should have an Entry Point in the
`magnum.template_definitions` group. This example exposes it's Template
Definition as `example_template = example_template:ExampleTemplate` in the
`magnum.template_definitions` group.

Installing Bay Templates
------------------------

Because Bay Templates are basically Python projects, they can be worked with
like any other Python project. They can be cloned from version control and
installed or uploaded to a package index and installed via utilities such as
pip.

Enabling a template is as simple as adding it's Entry Point to the
`enabled_definitions` config option in magnum.conf.::

    # Setup python environment and install Magnum

    $ virtualenv .venv
    $ source .venv/bin/active
    (.venv)$ git clone https://github.com/openstack/magnum.git
    (.venv)$ cd magnum
    (.venv)$ python setup.py install

    # List installed templates, notice default templates are enabled

    (.venv)$ magnum-template-manage list-templates
    Enabled Templates
      magnum_vm_atomic_k8s: /home/example/.venv/local/lib/python2.7/site-packages/magnum/templates/kubernetes/kubecluster.yaml
      magnum_vm_coreos_k8s: /home/example/.venv/local/lib/python2.7/site-packages/magnum/templates/kubernetes/kubecluster-coreos.yaml
    Disabled Templates

    # Install example template

    (.venv)$ cd contrib/templates/example
    (.venv)$ python setup.py install

    # List installed templates, notice example template is disabled

    (.venv)$ magnum-template-manage list-templates
    Enabled Templates
      magnum_vm_atomic_k8s: /home/example/.venv/local/lib/python2.7/site-packages/magnum/templates/kubernetes/kubecluster.yaml
      magnum_vm_coreos_k8s: /home/example/.venv/local/lib/python2.7/site-packages/magnum/templates/kubernetes/kubecluster-coreos.yaml
    Disabled Templates
      example_template: /home/example/.venv/local/lib/python2.7/site-packages/ExampleTemplate-0.1-py2.7.egg/example_template/example.yaml

    # Enable example template by setting enabled_definitions in magnum.conf

    (.venv)$ sudo mkdir /etc/magnum
    (.venv)$ sudo bash -c "cat > /etc/magnum/magnum.conf << END_CONF
    [bay]
    enabled_definitions=magnum_vm_atomic_k8s,magnum_vm_coreos_k8s,example_template
    END_CONF"

    # List installed templates, notice example template is now enabled

    (.venv)$ magnum-template-manage list-templates
    Enabled Templates
      example_template: /home/example/.venv/local/lib/python2.7/site-packages/ExampleTemplate-0.1-py2.7.egg/example_template/example.yaml
      magnum_vm_atomic_k8s: /home/example/.venv/local/lib/python2.7/site-packages/magnum/templates/kubernetes/kubecluster.yaml
      magnum_vm_coreos_k8s: /home/example/.venv/local/lib/python2.7/site-packages/magnum/templates/kubernetes/kubecluster-coreos.yaml
    Disabled Templates

    # Use --details argument to get more details about each template

    (.venv)$ magnum-template-manage list-templates --details
    Enabled Templates
      example_template: /home/example/.venv/local/lib/python2.7/site-packages/ExampleTemplate-0.1-py2.7.egg/example_template/example.yaml
         Server_Type  OS       CoE
         vm         example  example_coe
      magnum_vm_atomic_k8s: /home/example/.venv/local/lib/python2.7/site-packages/magnum/templates/kubernetes/kubecluster.yaml
         Server_Type   OS             CoE
         vm        fedora-atomic  kubernetes
      magnum_vm_coreos_k8s: /home/example/.venv/local/lib/python2.7/site-packages/magnum/templates/kubernetes/kubecluster-coreos.yaml
         Server_Type  OS      CoE
         vm         coreos  kubernetes
    Disabled Templates

