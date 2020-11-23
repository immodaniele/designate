# All Rights Reserved.
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


from oslo_log import versionutils
from oslo_policy import policy

from designate.common.policies import base

DEPRECATED_REASON = """
The zone export API now supports system scope and default roles.
"""

deprecated_zone_export = policy.DeprecatedRule(
    name="zone_export",
    check_str=base.RULE_ADMIN_OR_OWNER
)
deprecated_create_zone_export = policy.DeprecatedRule(
    name="create_zone_export",
    check_str=base.RULE_ADMIN_OR_OWNER
)
deprecated_find_zone_exports = policy.DeprecatedRule(
    name="find_zone_exports",
    check_str=base.RULE_ADMIN_OR_OWNER
)
deprecated_get_zone_export = policy.DeprecatedRule(
    name="get_zone_export",
    check_str=base.RULE_ADMIN_OR_OWNER
)
deprecated_update_zone_export = policy.DeprecatedRule(
    name="update_zone_export",
    check_str=base.RULE_ADMIN_OR_OWNER
)


rules = [
    policy.DocumentedRuleDefault(
        name="zone_export",
        check_str=base.SYSTEM_ADMIN_OR_PROJECT_MEMBER,
        scope_types=['system', 'project'],
        description="Retrive a Zone Export from the Designate Datastore",
        operations=[
            {
                'path': '/v2/zones/tasks/exports/{zone_export_id}/export',
                'method': 'GET'
            }
        ],
        deprecated_rule=deprecated_zone_export,
        deprecated_reason=DEPRECATED_REASON,
        deprecated_since=versionutils.deprecated.WALLABY
    ),
    policy.DocumentedRuleDefault(
        name="create_zone_export",
        check_str=base.SYSTEM_ADMIN_OR_PROJECT_MEMBER,
        scope_types=['system', 'project'],
        description="Create Zone Export",
        operations=[
            {
                'path': '/v2/zones/{zone_id}/tasks/export',
                'method': 'POST'
            }
        ],
        deprecated_rule=deprecated_create_zone_export,
        deprecated_reason=DEPRECATED_REASON,
        deprecated_since=versionutils.deprecated.WALLABY
    ),
    policy.DocumentedRuleDefault(
        name="find_zone_exports",
        check_str=base.SYSTEM_OR_PROJECT_READER,
        scope_types=['system', 'project'],
        description="List Zone Exports",
        operations=[
            {
                'path': '/v2/zones/tasks/exports',
                'method': 'GET'
            }
        ],
        deprecated_rule=deprecated_find_zone_exports,
        deprecated_reason=DEPRECATED_REASON,
        deprecated_since=versionutils.deprecated.WALLABY
    ),
    policy.DocumentedRuleDefault(
        name="get_zone_export",
        check_str=base.SYSTEM_OR_PROJECT_READER,
        scope_types=['system', 'project'],
        description="Get Zone Exports",
        operations=[
            {
                'path': '/v2/zones/tasks/exports/{zone_export_id}',
                'method': 'GET'
            }, {
                'path': '/v2/zones/tasks/exports/{zone_export_id}/export',
                'method': 'GET'
            }
        ],
        deprecated_rule=deprecated_get_zone_export,
        deprecated_reason=DEPRECATED_REASON,
        deprecated_since=versionutils.deprecated.WALLABY
    ),
    policy.DocumentedRuleDefault(
        name="update_zone_export",
        check_str=base.SYSTEM_ADMIN_OR_PROJECT_MEMBER,
        scope_types=['system', 'project'],
        description="Update Zone Exports",
        operations=[
            {
                'path': '/v2/zones/{zone_id}/tasks/export',
                'method': 'POST'
            }
        ],
        deprecated_rule=deprecated_update_zone_export,
        deprecated_reason=DEPRECATED_REASON,
        deprecated_since=versionutils.deprecated.WALLABY
    )
]


def list_rules():
    return rules
