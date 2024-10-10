# Copyright 2012 Managed I.T.
#
# Author: Kiall Mac Innes <kiall@managedit.ie>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
from oslo_log import log as logging

import designate.conf
from designate.notification_handler.base import BaseAddressHandler


CONF = designate.conf.CONF
LOG = logging.getLogger(__name__)


class NovaFixedHandler(BaseAddressHandler):
    """Handler for Nova's notifications"""
    __plugin_name__ = 'nova_fixed'

    def get_exchange_topics(self):
        exchange = CONF[self.name].control_exchange

        topics = [topic for topic in CONF[self.name].notification_topics]

        return (exchange, topics)

    def get_event_types(self):
        return [
            'compute.instance.create.end',
            'compute.instance.delete.start',
        ]

    def _get_ip_data(self, addr_dict):
        data = super()._get_ip_data(addr_dict)
        data['label'] = addr_dict['label']
        return data
    
    def _get_zone_for_project(self, context, project_id):
        # Cerca la zona associata al project_id
        zones = self.central_api.find_zones(context, {'tenant_id': project_id})
        if zones:
            return zones[0]
        return None

    def process_notification(self, context, event_type, payload):
        LOG.debug('NovaFixedHandler received notification - %s', event_type)
        LOG.debug('Payload: %s', payload)  # Nuovo log

        project_id = payload.get('tenant_id') or context.project_id
        LOG.debug('Project ID: %s', project_id)  # Nuovo log

        if not project_id:
            LOG.error('NovaFixedHandler: project_id is None, ignore the event.')
            return

        # Trova la zona per il project_id
        zone = self._get_zone_for_project(context, project_id)
        LOG.debug('Zone found: %s', zone)  # Nuovo log

        if not zone:
            LOG.error(f'NovaFixedHandler: No zone found for project {project_id}, ignore the event.')
            return

        if event_type == 'compute.instance.create.end':
            self._create(addresses=payload['fixed_ips'],
                         extra=payload,
                         zone_id=zone['id'],
                         resource_id=payload['instance_id'],
                         resource_type='instance')

        elif event_type == 'compute.instance.delete.start':
            self._delete(zone_id=zone['id'],
                         resource_id=payload['instance_id'],
                         resource_type='instance')