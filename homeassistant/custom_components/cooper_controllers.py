"""Support for adding switches from Cooper Z-Wave RFWD5 Scene Controllers."""
import datetime
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.components.zwave.const import DOMAIN as ZWAVE_DOMAIN
from homeassistant.components.zwave.const import EVENT_SCENE_ACTIVATED, DATA_DEVICES, EVENT_NETWORK_COMPLETE

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['zwave']
DOMAIN = 'cooper_controllers'
CONF_CONTROLLERS = 'controllers'

CONTROLLER_SCHEMA = {
    vol.Required('node_id'): vol.Coerce(int),
    vol.Required('indicator'): cv.entity_id
}

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_CONTROLLERS): vol.All(cv.ensure_list, 
            [CONTROLLER_SCHEMA])
    })
}, extra=vol.ALLOW_EXTRA)

def setup(hass, config):
    """Set up the Cooper Switch switch platform."""
    cooper_config = config[DOMAIN]

    controllers = {}
    for controller in cooper_config['controllers']:
        controllers[controller['node_id']] = controller['indicator']

    _LOGGER.info("Cooper config %s",str(controllers))

    def _update_cooper_indicator_state(event):
        node_id=event.data['node_id']
        scene_id=event.data['scene_id']
        if node_id in controllers:
            entity_id = controllers[node_id]
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

        # discovery.load_platform(
        #     hass, 'cooper_controllers', 'switch', discovered={},
        #     hass_config=config)
    # wait for zwave ready

    def _find_cooper_controllers(event):
        _LOGGER.info("%s",str(hass.data['entity_registry']))

    hass.bus.listen(EVENT_SCENE_ACTIVATED, _update_cooper_indicator_state)

    #hass.bus.listen_once(EVENT_NETWORK_COMPLETE, _find_cooper_controllers)
    return True