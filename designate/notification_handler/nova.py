# -*- coding: utf-8 -*-

# Copyright 2016 Telefónica Investigación y Desarrollo, S.A.U
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
from designate.context import DesignateContext
from designate import exceptions
from designate.notification_handler.base import NotificationHandler
from designate.objects import Record
from designate.objects import RecordSet
from designate.objects import RecordList


CONF = designate.conf.CONF
LOG = logging.getLogger(__name__)


class BaseEnhancedHandler(NotificationHandler):
    """Base Enhanced Handler"""

    def get_exchange_topics(self):
        exchange = CONF[self.name].control_exchange
        topics = [topic for topic in cfg.CONF[self.name].notification_topics]
        return (exchange, topics)

    def _get_context(self, tenant_id=None):
        if tenant_id:
            return DesignateContext.get_admin_context(tenant=tenant_id, edit_managed_records=True)
        else:
            return DesignateContext.get_admin_context(all_tenants=True, edit_managed_records=True)

    def _get_zone(self, context, hostname):
        tenant_zones =  self.central_api.find_zones(context, {'tenant_id': context.tenant})
        valid_zones = [x for x in tenant_zones 
                       if hostname.endswith(x.name[:-1])
                       and (not x.name in cfg.CONF[self.name].zone_id.split(','))]
        if not valid_zones:
            raise exceptions.ZoneNotFound()
        return sorted(valid_zones, key=lambda x: len(x.name), reverse=True)[0]

    def _get_reverse_fqdn(self, address, version):
        if version == 6:
            # See https://en.wikipedia.org/wiki/IPv6_address#IPv6_addresses_in_the_Domain_Name_System
            # Convert fdda:5cc1:23:4::1f into f100000000000000400032001cc5addf
            revaddr = map(lambda x: x.ljust(4, '0'), address[::-1].split(':')).join('')
            # Add a dot between each character and the suffix for IP v6
            return list(revaddr).join('.') + '.ip6.arpa.'
        else:
            return '.'.join(address.split('.')[::-1]) + '.in-addr.arpa.'

    def _get_reverse_zone(self, context, host_reverse_fqdn=None):
        zones = self.central_api.find_zones(context)
        reverse_zones = [x for x in zones if x.name.endswith('.arpa.')]
        if host_reverse_fqdn:
            reverse_zones = list(filter(
                lambda x: host_reverse_fqdn.endswith(x.name), reverse_zones))
        if len(reverse_zones) == 0:
            return None
        return sorted(reverse_zones, key=lambda x: len(x.name), reverse=True)[0]

    def _get_host_fqdn(self, zone, hostname, interface):
        return "%s." % hostname

    def _create_or_replace_recordset(self, context, records, zone_id, name,
                                    type, ttl=None):
        name = name.encode('idna').decode('utf-8')
        found_recordset = self.central_api.find_recordsets(
            context, {'zone_id': zone_id, 'name': name})
        if len(found_recordset) > 0:
            LOG.warn('Found already existing recordset %s with name %s, '
                     'deleting it.', found_recordset[0].id,
                     found_recordset[0].name)
            self.central_api.delete_recordset(
                context, zone_id, found_recordset[0].id,
                increment_serial=False)
        recordset = RecordSet(name=name, type=type, ttl=ttl)
        recordset.records = RecordList(objects=records)
        recordset = self.central_api.create_recordset(
            context, zone_id, recordset
        )
        for record in records:
            recordset.records.append(record)
        LOG.debug('Created recordset %s in zone %s', recordset['id'], zone_id)
        return recordset


    def _create_record(self, context, managed, zone, host_fqdn, interface):
        LOG.debug('Create record for host: %s and ip_version: %s', host_fqdn,
                 interface['version'])
        recordset_type = 'AAAA' if interface['version'] == 6 else 'A'
        record = Record(**dict(managed, data=interface['address']))
        self._create_or_replace_recordset(context, [record], zone.id,
                                          host_fqdn, recordset_type)
        LOG.info('Created record %s with data %s'
                 % (host_fqdn, record['data']))

    def _create_reverse_record(self, context, managed, host_fqdn, interface):
        LOG.debug('Create reverse record for host %s and address: %s',
                  host_fqdn, interface['address'])
        host_reverse_fqdn = self._get_reverse_fqdn(interface['address'],
                                                   interface['version'])

        all_tenants_context = self._get_context()
        reverse_zone = self._get_reverse_zone(all_tenants_context, 
                                              host_reverse_fqdn)
        if not reverse_zone:
            LOG.info('No reverse zone found for host %s and address %s',
                     host_fqdn, interface['address'])
            return

        record = Record(**dict(managed, data=host_fqdn))
        self._create_or_replace_recordset(all_tenants_context, [record],
                                          reverse_zone.id,
                                          host_reverse_fqdn, 'PTR')
        LOG.info('Created PTR record %s for host %s'
                 % (host_reverse_fqdn, host_fqdn))

    def _create_records(self, context, managed, payload):
        try:
            hostname = payload['hostname']
            zone = self._get_zone(context, hostname)
        except exceptions.ZoneNotFound:
            LOG.warn('There is no zone registered for tenant: %s', context.tenant)
        except Exception as e:
            LOG.error('Error getting the zone for tenant: %s. %s', context.tenant, e)
        else:
            ipv4_interfaces = [x for x in payload['fixed_ips'] if x['version'] == 4]
            ipv6_interfaces = [x for x in payload['fixed_ips'] if x['version'] == 6]
            if ipv4_interfaces:
                self._create_record(context, managed, zone, "%s." % hostname,
                                    ipv4_interfaces[0])
                self._create_reverse_record(context, managed, "%s." % hostname,
                                    ipv4_interfaces[0])
            if ipv6_interfaces:
                self._create_record(context, managed, zone, "%s." % hostname,
                                    ipv6_interfaces[0])
                self._create_reverse_record(context, managed, "%s." % hostname,
                                    ipv6_interfaces[0])

    def _delete_records(self, all_tenants_context, managed, payload):
        records = self.central_api.find_records(all_tenants_context,
                                                managed)
        LOG.debug('Deleting records for instance %s(%s)', len(records),
                 payload['instance_id'], payload['hostname'])
        LOG.info('Deleting records for instance %s: %s'
                 % (payload['instance_id'], [x['data'] for x in records]))
        if len(records) == 0:
            LOG.debug('No record found to be deleted')
        else:
            for record in records:
                LOG.debug('Deleting record %s(data: %s)',
                          record['id'], record['data'])
                try:
                    self.central_api.delete_record(all_tenants_context,
                                                   record['zone_id'],
                                                   record['recordset_id'],
                                                   record['id'])
                except exceptions.ZoneNotFound:
                    LOG.warn('There is no zone registered with id: %s', record['zone_id'])
                except Exception as e:
                    LOG.error('Error deleting record: %s. %s', record['id'], e)


class NovaFixedHandler(BaseEnhancedHandler):
    """Nova Enhanced Handler"""
    __plugin_name__ = 'nova_fixed'

    def get_event_types(self):
        return [
            'compute.instance.create.end',
            'compute.instance.delete.start',
        ]

    def process_notification(self, context, event_type, payload):
        LOG.debug('NovaCustomHandler notification: %s. %s', event_type, payload)
        tenant_id = payload['tenant_id']

        managed = {
            'managed': True,
            'managed_plugin_name': self.get_plugin_name(),
            'managed_plugin_type': self.get_plugin_type(),
            'managed_resource_type': 'instance',
            'managed_resource_id': payload['instance_id']
        }

        if event_type == 'compute.instance.create.end':
            self._create_records(self._get_context(tenant_id), managed, payload)
        elif event_type == 'compute.instance.delete.start':
            self._delete_records(self._get_context(), managed, payload)