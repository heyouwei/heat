# vim: tabstop=4 shiftwidth=4 softtabstop=4

#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import collections
import functools
import six

from heat.engine import properties
from heat.engine.resources.software_config import software_config as sc
from heat.engine.resources.software_config import software_deployment as sd


class StructuredConfig(sc.SoftwareConfig):
    '''
    This resource is like OS::Heat::SoftwareConfig except that the config
    property is represented by a Map rather than a String.

    This is useful for configuration tools which use YAML or JSON as their
    configuration syntax. The resulting configuration is transferred,
    stored and returned by the software_configs API as parsed JSON.
    '''

    PROPERTIES = (
        GROUP,
        CONFIG,
        OPTIONS,
        INPUTS,
        OUTPUTS
    ) = (
        sc.SoftwareConfig.GROUP,
        sc.SoftwareConfig.CONFIG,
        sc.SoftwareConfig.OPTIONS,
        sc.SoftwareConfig.INPUTS,
        sc.SoftwareConfig.OUTPUTS
    )

    properties_schema = {
        GROUP: sc.SoftwareConfig.properties_schema[GROUP],
        OPTIONS: sc.SoftwareConfig.properties_schema[OPTIONS],
        INPUTS: sc.SoftwareConfig.properties_schema[INPUTS],
        OUTPUTS: sc.SoftwareConfig.properties_schema[OUTPUTS],
        CONFIG: properties.Schema(
            properties.Schema.MAP,
            _('Map representing the configuration data structure which will '
              'be serialized to JSON format.')
        )
    }


class StructuredDeployment(sd.SoftwareDeployment):
    '''
    A deployment resource like OS::Heat::SoftwareDeployment, but which
    performs input value substitution on the config defined by a
    OS::Heat::StructuredConfig resource.

    Some configuration tools have no concept of inputs, so the input value
    substitution needs to occur in the deployment resource. An example of this
    is the JSON metadata consumed by the cfn-init tool.

    Where the config contains {get_input: input_name} this will be substituted
    with the value of input_name in this resource's input_values. If get_input
    needs to be passed through to the substituted configuration then a
    different input_key property value can be specified.
    '''

    PROPERTIES = (
        CONFIG,
        SERVER,
        INPUT_VALUES,
        DEPLOY_ACTIONS,
        NAME,
        SIGNAL_TRANSPORT,
        INPUT_KEY
    ) = (
        sd.SoftwareDeployment.CONFIG,
        sd.SoftwareDeployment.SERVER,
        sd.SoftwareDeployment.INPUT_VALUES,
        sd.SoftwareDeployment.DEPLOY_ACTIONS,
        sd.SoftwareDeployment.NAME,
        sd.SoftwareDeployment.SIGNAL_TRANSPORT,
        'input_key'
    )

    _sd_ps = sd.SoftwareDeployment.properties_schema

    properties_schema = {
        CONFIG: _sd_ps[CONFIG],
        SERVER: _sd_ps[SERVER],
        INPUT_VALUES: _sd_ps[INPUT_VALUES],
        DEPLOY_ACTIONS: _sd_ps[DEPLOY_ACTIONS],
        SIGNAL_TRANSPORT: _sd_ps[SIGNAL_TRANSPORT],
        NAME: _sd_ps[NAME],
        INPUT_KEY: properties.Schema(
            properties.Schema.STRING,
            _('Name of key to use for substituting inputs during deployment'),
            default='get_input',
        )
    }

    def _build_derived_config(self, action, source,
                              derived_inputs, derived_options):
        cfg = source.get(sc.SoftwareConfig.CONFIG)
        input_key = self.properties.get(self.INPUT_KEY)

        inputs = dict((i['name'], i['value']) for i in derived_inputs)

        return self.parse(inputs, input_key, cfg)

    @staticmethod
    def parse(inputs, input_key, snippet):
        parse = functools.partial(
            StructuredDeployment.parse, inputs, input_key)

        if isinstance(snippet, collections.Mapping):
            if len(snippet) == 1:
                fn_name, args = next(six.iteritems(snippet))
                if fn_name == input_key:
                    if isinstance(args, basestring):
                        return inputs.get(args)
            return dict((k, parse(v)) for k, v in six.iteritems(snippet))
        elif (not isinstance(snippet, basestring) and
              isinstance(snippet, collections.Iterable)):
            return [parse(v) for v in snippet]
        else:
            return snippet


class StructuredDeployments(sd.SoftwareDeployments):

    PROPERTIES = (
        SERVERS,
        CONFIG,
        INPUT_VALUES,
        DEPLOY_ACTIONS,
        NAME,
        SIGNAL_TRANSPORT,
        INPUT_KEY,
    ) = (
        sd.SoftwareDeployments.SERVERS,
        sd.SoftwareDeployments.CONFIG,
        sd.SoftwareDeployments.INPUT_VALUES,
        sd.SoftwareDeployments.DEPLOY_ACTIONS,
        sd.SoftwareDeployments.NAME,
        sd.SoftwareDeployments.SIGNAL_TRANSPORT,
        StructuredDeployment.INPUT_KEY
    )

    _sds_ps = sd.SoftwareDeployments.properties_schema

    properties_schema = {
        SERVERS: _sds_ps[SERVERS],
        CONFIG: _sds_ps[CONFIG],
        INPUT_VALUES: _sds_ps[INPUT_VALUES],
        DEPLOY_ACTIONS: _sds_ps[DEPLOY_ACTIONS],
        SIGNAL_TRANSPORT: _sds_ps[SIGNAL_TRANSPORT],
        NAME: _sds_ps[NAME],
        INPUT_KEY: StructuredDeployment.properties_schema[INPUT_KEY],
    }

    def _build_resource_definition(self, include_all=False):
        p = self.properties
        return {
            self.RESOURCE_DEF_TYPE: 'OS::Heat::StructuredDeployment',
            self.RESOURCE_DEF_PROPERTIES: {
                self.CONFIG: p[self.CONFIG],
                self.INPUT_VALUES: p[self.INPUT_VALUES],
                self.DEPLOY_ACTIONS: p[self.DEPLOY_ACTIONS],
                self.SIGNAL_TRANSPORT: p[self.SIGNAL_TRANSPORT],
                self.NAME: p[self.NAME],
                self.INPUT_KEY: p[self.INPUT_KEY],
            }
        }


def resource_mapping():
    return {
        'OS::Heat::StructuredConfig': StructuredConfig,
        'OS::Heat::StructuredDeployment': StructuredDeployment,
        'OS::Heat::StructuredDeployments': StructuredDeployments,
    }
