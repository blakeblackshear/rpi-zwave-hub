"""Switches for Cooper Controllers."""
import datetime
import logging

from homeassistant.components.switch import SwitchDevice
from homeassistant.components.zwave.const import SERVICE_SET_NODE_VALUE, SERVICE_REFRESH_NODE_VALUE
from homeassistant.helpers.event import async_track_state_change, async_call_later

DEPENDENCIES = ['cooper_controllers']
DOMAIN = 'cooper_controllers'

_LOGGER = logging.getLogger(__name__)

BUTTON_VALUES = {
    1: 1,
    2: 2,
    3: 4,
    4: 8,
    5: 16
}

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Cooper Controller switch platform."""
    switches = []

    controllers = hass.data[DOMAIN]

    for node_id in controllers:
        for button in [1,2,3,4,5]:
            switches.append(CooperControllerSwitch(node_id, controllers[node_id], button))

    add_entities(switches)


class CooperControllerSwitch(SwitchDevice):
    """A Cooper Controller button."""

    def __init__(self, node_id, controller, button):
        """Initialize a button for a Cooper Controller."""
        self._node_id = node_id
        self._controller = controller
        self._button = button
        self._state = False
        self._indicator_entity_id = controller['indicator']
        self._associations = self._controller['groups'][self._button]['associations']
    
    async def async_added_to_hass(self):
        """Subscribe to state changes for indicator events."""
        def _refresh_associated(*_):
            for association in self._associations:
                entity = self.hass.states.get(association)
                data = {
                    "node_id": entity.attributes['node_id'],
                    "value_id": entity.attributes['value_id']
                }
                self.hass.async_add_job(self.hass.services.async_call('zwave', SERVICE_REFRESH_NODE_VALUE, data))

        def _state_updated(entity_id, old_state, new_state):
            """Schedule an update."""
            async_call_later(self.hass, 4, _refresh_associated)
            self.async_schedule_update_ha_state()

        def _sync_associated(entity_id, old_state, new_state):
            all_off = True
            for association in self._associations:
                if self.hass.states.get(association).state == 'on':
                    all_off = False
                    break
            
            if all_off and self.is_on:
                self.turn_off()
            elif not all_off and not self.is_on:
                self.turn_on()

        async_track_state_change(
            self.hass, self._indicator_entity_id, _state_updated
        )

        for associated_entity in self._associations:
            async_track_state_change(
                self.hass, associated_entity, _sync_associated
            )
    
    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name of the switch."""
        return "Node {0} Button {1}".format(self._node_id, self._button)

    @property
    def is_on(self):
        """Get the state of the button based on the indicator value."""
        indicator_state = self.hass.states.get(self._indicator_entity_id)
        indicator_value = int(indicator_state.state)
        return indicator_value & BUTTON_VALUES[self._button] != 0

    def turn_on(self, **kwargs):
        """Turn on the led for the button."""
        indicator_state = self.hass.states.get(self._indicator_entity_id)
        indicator_value = int(indicator_state.state)

        if indicator_value & BUTTON_VALUES[self._button] != 0:
            return

        data = {
            "node_id": self._node_id,
            "value_id": indicator_state.attributes['value_id'],
            "value": indicator_value + BUTTON_VALUES[self._button]
        }
        # set the indicator value ahead of time to ensure turning on or off a different switch doesn't
        # reset the indicator value. 
        self.hass.states.set(self._indicator_entity_id, data['value'], indicator_state.attributes)
        # actually set the indicator value
        self.hass.async_add_job(self.hass.services.async_call('zwave', SERVICE_SET_NODE_VALUE, data))

    def turn_off(self, **kwargs):
        """Turn on the led for the button."""
        indicator_state = self.hass.states.get(self._indicator_entity_id)
        indicator_value = int(indicator_state.state)

        if indicator_value & BUTTON_VALUES[self._button] == 0:
            return

        data = {
            "node_id": self._node_id,
            "value_id": indicator_state.attributes['value_id'],
            "value": indicator_value - BUTTON_VALUES[self._button]
        }
        # set the indicator value ahead of time to ensure turning on or off a different switch doesn't
        # reset the indicator value. 
        self.hass.states.set(self._indicator_entity_id, data['value'], indicator_state.attributes)
        # actually set the indicator value
        self.hass.async_add_job(self.hass.services.async_call('zwave', SERVICE_SET_NODE_VALUE, data))
