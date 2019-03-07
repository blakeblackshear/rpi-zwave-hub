"""Support for adding switches from Cooper Z-Wave RFWD5 Scene Controllers."""
import datetime
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.components.zwave.const import DOMAIN as ZWAVE_DOMAIN
from homeassistant.components.zwave.const import (
    EVENT_SCENE_ACTIVATED, DATA_DEVICES, EVENT_NETWORK_COMPLETE, EVENT_NODE_EVENT, 
    SERVICE_REFRESH_NODE_VALUE, DATA_NETWORK, COMMAND_CLASS_INDICATOR, EVENT_NETWORK_READY,
    EVENT_NETWORK_COMPLETE_SOME_DEAD)

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['zwave']
DOMAIN = 'cooper_controllers'
CONF_CONTROLLERS = 'controllers'

def setup(hass, config):
    """Set up the Cooper Switch switch platform."""
    controllers = {}

    def _discover_cooper_switches(states):
        for state in states:
            if (state.domain == 'zwave' and 
            'product_name' in state.attributes and
            state.attributes['product_name'] == 'RFWC5/RFWDC Scene Controller'):
                controllers[state.attributes['node_id']] = {}

    def _populate_indicators(states):
        network = hass.data.get(DATA_NETWORK)
        for node_id in controllers:
            node = network.nodes.get(node_id)
            if node is None:
                return
            
            # fetch the value id for the indicator
            indicator_value_id = None
            if node.has_command_class(COMMAND_CLASS_INDICATOR):
                for value_id in node.get_values(
                        class_id=COMMAND_CLASS_INDICATOR):
                    indicator_value_id = value_id
                    break

            # find the indicator sensor entity id
            for state in states:
                if (state.domain == 'sensor' and 
                'value_id' in state.attributes and
                state.attributes['value_id'] == str(indicator_value_id)):
                    controllers[node_id]['indicator'] = state.entity_id

    def _populate_associations(states):
        # build a map of node_id to entity_id for lights and switches
        zwave_nodes = {}
        for state in states:
            if 'node_id' not in state.attributes:
                continue
            if state.domain not in ['switch', 'light']:
                continue
            node_id = state.attributes['node_id']
            zwave_nodes[node_id] = state.entity_id

        # lookup associations and map node_ids to entity ids
        network = hass.data.get(DATA_NETWORK)
        for node_id in controllers:
            node = network.nodes.get(node_id)
            if node is None:
                return
            groupdata = node.groups
            groups = {}
            for key, value in groupdata.items():
                associated_entities = [zwave_nodes[association] for association in value.associations
                                        if association in zwave_nodes]
                groups[key] = {'associations': associated_entities}
            controllers[node_id]['groups'] = groups

    def _update_cooper_indicator_state(event):
        node_id=event.data['node_id']
        scene_id=event.data['scene_id']
        if node_id in controllers:
            entity_id = controllers[node_id]['indicator']
            indicator_state = hass.states.get(entity_id)
            indicator_value = int(indicator_state.state)
            if scene_id==1 and (indicator_value & 1)==0:
                indicator_value = indicator_value+1
            elif scene_id==2 and (indicator_value & 2)==0:
                indicator_value = indicator_value+2
            elif scene_id==3 and (indicator_value & 4)==0:
                indicator_value = indicator_value+4
            elif scene_id==4 and (indicator_value & 8)==0:
                indicator_value = indicator_value+8
            elif scene_id==5 and (indicator_value & 16)==0:
                indicator_value = indicator_value+16
            hass.states.set(entity_id, indicator_value, indicator_state.attributes)

    def _refresh_cooper_indicator_state(event):
        node_id=event.data['node_id']

        if node_id in controllers:
            entity_id = controllers[node_id]['indicator']
            indicator_state = hass.states.get(entity_id)

            data = {
                "node_id": node_id,
                "value_id": indicator_state.attributes['value_id']
            }
            hass.async_add_job(hass.services.async_call('zwave', SERVICE_REFRESH_NODE_VALUE, data))

    def _create_cooper_switches(event):
        if len(controllers)>0:
            return
        states = hass.states.all()
        _discover_cooper_switches(states)
        _populate_indicators(states)
        _populate_associations(states)
        _LOGGER.info("Discovered Cooper Controllers %s",str(controllers))
        hass.data[DOMAIN] = controllers
        discovery.load_platform(
            hass, 'switch', 'cooper_controllers', discovered={},
            hass_config=config)

    hass.bus.listen(EVENT_SCENE_ACTIVATED, _update_cooper_indicator_state)
    hass.bus.listen(EVENT_NODE_EVENT, _refresh_cooper_indicator_state)
    hass.bus.listen_once(EVENT_NETWORK_READY, _create_cooper_switches)
    hass.bus.listen_once(EVENT_NETWORK_COMPLETE, _create_cooper_switches)
    hass.bus.listen_once(EVENT_NETWORK_COMPLETE_SOME_DEAD, _create_cooper_switches)
    return True